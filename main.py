from fastmcp import FastMCP
import os
import sqlite3
import json
import datetime
import calendar as cal
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def create_calendar_event(date, amount, category, note):
    service = get_calendar_service()
    event = {
        'summary': f"💸 {category}: {amount}",
        'description': note or '',
        'start': {'date': date, 'timeZone': 'Asia/Kathmandu'},
        'end':   {'date': date, 'timeZone': 'Asia/Kathmandu'},
    }
    service.events().insert(calendarId='primary', body=event).execute()


DB_PATH = os.path.join(BASE_DIR, 'expenses.db')
CATEGORIES_PATH = os.path.join(BASE_DIR, 'categories.json')

mcp = FastMCP("ExpenseTracker")


# ─────────────────────────────────────────────
# Database Initialization
# ─────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Expenses
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                subcategory TEXT DEFAULT NULL,
                note        TEXT DEFAULT NULL
            )
        """)
        # Budgets — one row per (category, month)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                category     TEXT NOT NULL,
                month        TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                UNIQUE(category, month)
            )
        """)
        # Credits (income) — multiple entries per month allowed
        # source examples: 'salary', 'freelance', 'rental', 'bonus', etc.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS credits (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                date   TEXT NOT NULL,       -- YYYY-MM-DD
                amount REAL NOT NULL,
                source TEXT NOT NULL,       -- e.g. 'salary', 'freelance'
                note   TEXT DEFAULT NULL
            )
        """)

init_db()


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _current_month() -> str:
    return datetime.date.today().strftime('%Y-%m')


def _month_range(month: str):
    year, mon = int(month[:4]), int(month[5:7])
    last_day = cal.monthrange(year, mon)[1]
    return f"{month}-01", f"{month}-{last_day:02d}"


def _spent_this_month(category: str, month: str) -> float:
    start, end = _month_range(month)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses "
            "WHERE category = ? AND date BETWEEN ? AND ?",
            (category, start, end)
        )
        return cur.fetchone()[0]


def _total_spent_month(month: str) -> float:
    start, end = _month_range(month)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date BETWEEN ? AND ?",
            (start, end)
        )
        return cur.fetchone()[0]


def _total_credits_month(month: str) -> float:
    start, end = _month_range(month)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM credits WHERE date BETWEEN ? AND ?",
            (start, end)
        )
        return cur.fetchone()[0]


def _total_budgeted_month(month: str) -> float:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(limit_amount), 0) FROM budgets WHERE month = ?",
            (month,)
        )
        return cur.fetchone()[0]


def _get_budget(category: str, month: str) -> float | None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT limit_amount FROM budgets WHERE category = ? AND month = ?",
            (category, month)
        )
        row = cur.fetchone()
        return row[0] if row else None


def _build_alert(category: str, spent: float, budget: float) -> str | None:
    if budget <= 0:
        return None
    pct = (spent / budget) * 100
    if pct >= 100:
        return (
            f"🚨 BUDGET EXCEEDED — {category.upper()}\n"
            f"   Spent: {spent:,.0f} | Budget: {budget:,.0f} | "
            f"Over by: {spent - budget:,.0f} ({pct:.0f}%)"
        )
    elif pct >= 80:
        return (
            f"⚠️  Budget Warning — {category}\n"
            f"   Spent {pct:.0f}% of your {budget:,.0f} budget  "
            f"({spent:,.0f} used, {budget - spent:,.0f} left)"
        )
    return None


def _weekly_pace_alert(category: str, month: str, budget: float) -> str | None:
    today = datetime.date.today()
    day_of_month = today.day
    year, mon = int(month[:4]), int(month[5:7])
    days_in_month = cal.monthrange(year, mon)[1]

    if day_of_month < 3 or budget <= 0:
        return None

    expected_fraction = day_of_month / days_in_month
    actual_spent = _spent_this_month(category, month)
    expected_spent = budget * expected_fraction

    if actual_spent > expected_spent * 1.20:
        projected = (actual_spent / day_of_month) * days_in_month
        return (
            f"💡 Spending Pace Alert — {category}\n"
            f"   You're spending faster than usual. "
            f"Projected month-end: {projected:,.0f} (budget: {budget:,.0f})"
        )
    return None


def _credit_health_alerts(month: str) -> list[str]:
    """
    Cross-check total income vs total budgeted vs total spent for the month.
    Returns a list of alert strings (may be empty).
    """
    alerts = []
    total_income = _total_credits_month(month)
    total_budgeted = _total_budgeted_month(month)
    total_spent = _total_spent_month(month)

    if total_income <= 0:
        return alerts  # no income logged yet — skip cross-checks

    unallocated = total_income - total_budgeted
    net_savings = total_income - total_spent

    if total_budgeted > total_income:
        alerts.append(
            f"🚨 Over-Allocated — Your budgets ({total_budgeted:,.0f}) exceed "
            f"your income ({total_income:,.0f}) by {total_budgeted - total_income:,.0f}"
        )
    elif unallocated > 0:
        alerts.append(
            f"💡 Unallocated Income — {unallocated:,.0f} of your {total_income:,.0f} "
            f"income has no budget assigned yet."
        )

    if total_spent > total_income:
        alerts.append(
            f"🚨 Spending Exceeds Income — You've spent {total_spent:,.0f} but "
            f"only earned {total_income:,.0f} this month. Deficit: {total_spent - total_income:,.0f}"
        )
    elif net_savings >= 0:
        savings_pct = (net_savings / total_income) * 100
        if savings_pct < 10:
            alerts.append(
                f"⚠️  Low Savings — You're saving only {savings_pct:.1f}% of your income "
                f"({net_savings:,.0f} of {total_income:,.0f})."
            )

    return alerts


# ─────────────────────────────────────────────
# MCP Tools — Expenses
# ─────────────────────────────────────────────

@mcp.tool()
def add_expense(date: str, amount: float, category: str,
                subcategory: str = '', note: str = '') -> dict:
    """
    Add a new expense to the tracker (saves to database only).
    The Google Calendar event will be created separately after user approval.

    Args:
        date:        The date of the expense in YYYY-MM-DD format (e.g. '2026-03-20')
        amount:      The amount spent as a number (e.g. 1200)
        category:    The category of the expense (e.g. 'food', 'transport')
        subcategory: Optional subcategory (e.g. 'groceries')
        note:        Optional note or description

    After saving, automatically checks active budgets and income for the month
    and returns any alert messages if thresholds are crossed.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            'INSERT INTO expenses (date, amount, category, subcategory, note) '
            'VALUES (?, ?, ?, ?, ?)',
            (date, amount, category, subcategory, note)
        )
        expense_id = cur.lastrowid

    month = date[:7]
    alerts = []

    # Category budget alerts
    budget = _get_budget(category, month)
    if budget is not None:
        spent = _spent_this_month(category, month)
        a = _build_alert(category, spent, budget)
        if a:
            alerts.append(a)
        p = _weekly_pace_alert(category, month, budget)
        if p:
            alerts.append(p)

    # Credit / income health alerts
    alerts.extend(_credit_health_alerts(month))

    result = {
        'status': 'ok',
        'id': expense_id,
        'date': date,
        'amount': amount,
        'category': category,
        'note': note,
    }
    if alerts:
        result['alerts'] = alerts
    return result


@mcp.tool()
def edit_expense(expense_id: int, date: str = None, amount: float = None,
                category: str = None, subcategory: str = None, note: str = None) -> dict:
    """
    Edit an existing expense entry.
    Only the fields you provide will be updated — the rest stay unchanged.

    Args:
        expense_id:  The ID of the expense to edit (use list_expenses to find it).
        date:        New date in YYYY-MM-DD format.
        amount:      New amount.
        category:    New category.
        subcategory: New subcategory.
        note:        New note.

    Example prompts:
        "I entered the grocery amount wrong, it should be 950 not 1200. Fix expense 5."
        "Change the category of expense 3 to transport."
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT date, amount, category, subcategory, note FROM expenses WHERE id = ?",
            (expense_id,)
        )
        row = cur.fetchone()
        if not row:
            return {'status': 'error', 'message': f"No expense found with id {expense_id}."}

        old_date, old_amount, old_cat, old_sub, old_note = row
        new_date   = date        if date        is not None else old_date
        new_amount = amount      if amount      is not None else old_amount
        new_cat    = category    if category    is not None else old_cat
        new_sub    = subcategory if subcategory is not None else old_sub
        new_note   = note        if note        is not None else old_note

        conn.execute(
            "UPDATE expenses SET date=?, amount=?, category=?, subcategory=?, note=? WHERE id=?",
            (new_date, new_amount, new_cat, new_sub, new_note, expense_id)
        )

    # Re-check budget alerts for the (possibly new) category and month
    month  = new_date[:7]
    alerts = []
    budget = _get_budget(new_cat, month)
    if budget is not None:
        spent = _spent_this_month(new_cat, month)
        a = _build_alert(new_cat, spent, budget)
        if a:
            alerts.append(a)
        p = _weekly_pace_alert(new_cat, month, budget)
        if p:
            alerts.append(p)
    alerts.extend(_credit_health_alerts(month))

    result = {
        'status': 'ok',
        'message': f"Expense {expense_id} updated.",
        'updated': {
            'id': expense_id, 'date': new_date, 'amount': new_amount,
            'category': new_cat, 'subcategory': new_sub, 'note': new_note,
        }
    }
    if alerts:
        result['alerts'] = alerts
    return result


@mcp.tool()
def delete_expense(expense_id: int) -> dict:
    """
    Delete an expense entry by its ID.

    Args:
        expense_id: The ID of the expense to remove (use list_expenses to find it).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,))
        if not cur.fetchone():
            return {'status': 'error', 'message': f"No expense found with id {expense_id}."}
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return {'status': 'ok', 'message': f"Expense {expense_id} deleted."}


@mcp.tool()
def add_to_calendar(date: str, amount: float, category: str, note: str = '') -> dict:
    """
    Create a Google Calendar event for an expense.
    Only call this tool AFTER the user has explicitly approved adding to calendar.

    Args:
        date:     The date in YYYY-MM-DD format
        amount:   The expense amount
        category: The expense category
        note:     Optional note
    """
    try:
        create_calendar_event(date, amount, category, note)
        return {'status': 'ok', 'message': f'Calendar event created: {category} {amount} on {date}'}
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}


@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> list:
    """List expenses between start_date and end_date."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, date, amount, category, subcategory, note "
            "FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC, id ASC",
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def summarize(start_date: str, end_date: str, category: str = None) -> list:
    """Summarize expenses by category."""
    with sqlite3.connect(DB_PATH) as conn:
        query = ("SELECT category, SUM(amount) AS total_amount FROM expenses "
                 "WHERE date BETWEEN ? AND ?")
        params = [start_date, end_date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " GROUP BY category ORDER BY category ASC"
        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# ─────────────────────────────────────────────
# MCP Tools — Credits (Income)
# ─────────────────────────────────────────────

@mcp.tool()
def add_credit(date: str, amount: float, source: str, note: str = '') -> dict:
    """
    Log income / credit for the month (salary, freelance payment, rental, bonus, etc.).
    This is the foundation of your budget — knowing what you earned tells the system
    how much you can actually spend.

    Args:
        date:   Date the income was received, in YYYY-MM-DD format.
        amount: Amount received (e.g. 75000 for a monthly salary).
        source: Income source label, e.g. 'salary', 'freelance', 'rental', 'bonus',
                'interest', 'gift', 'refund', 'other'.
        note:   Optional description.

    Example prompts:
        "I got my salary of 75,000 today."
        "Log 15,000 freelance payment received on 2026-03-25."
        "Add a rental income of 8,000 for March."
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO credits (date, amount, source, note) VALUES (?, ?, ?, ?)",
            (date, amount, source, note)
        )
        credit_id = cur.lastrowid

    month = date[:7]
    total_income = _total_credits_month(month)
    total_budgeted = _total_budgeted_month(month)
    total_spent = _total_spent_month(month)

    unallocated = total_income - total_budgeted
    net = total_income - total_spent

    result = {
        'status': 'ok',
        'id': credit_id,
        'date': date,
        'amount': amount,
        'source': source,
        'month_summary': {
            'total_income': round(total_income, 2),
            'total_budgeted': round(total_budgeted, 2),
            'total_spent': round(total_spent, 2),
            'unallocated': round(unallocated, 2),
            'net_savings': round(net, 2),
        }
    }

    # Warn if budgets already exceed new income total
    if total_budgeted > total_income:
        result['alert'] = (
            f"⚠️  Your current budgets ({total_budgeted:,.0f}) exceed your "
            f"total income so far ({total_income:,.0f}). "
            f"Consider adjusting your budgets."
        )

    return result


@mcp.tool()
def list_credits(month: str = '') -> list:
    """
    List all income / credit entries for a given month.

    Args:
        month: Month in YYYY-MM format. Defaults to current month.
    """
    if not month:
        month = _current_month()
    start, end = _month_range(month)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, date, amount, source, note FROM credits "
            "WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start, end)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def edit_credit(credit_id: int, amount: float = None, source: str = None,
               date: str = None, note: str = None) -> dict:
    """
    Edit an existing credit / income entry.
    Only the fields you provide will be updated — the rest stay unchanged.

    Args:
        credit_id: The ID of the entry to edit (use list_credits to find it).
        amount:    New amount (e.g. if your salary changed or you entered it wrong).
        source:    New source label (e.g. 'salary', 'freelance').
        date:      New date in YYYY-MM-DD format.
        note:      New note / description.

    Example prompts:
        "My salary was actually 80,000 not 75,000, fix credit 1."
        "Change the source of credit 2 to freelance."
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT date, amount, source, note FROM credits WHERE id = ?",
                           (credit_id,))
        row = cur.fetchone()
        if not row:
            return {'status': 'error', 'message': f"No credit found with id {credit_id}."}

        old_date, old_amount, old_source, old_note = row
        new_date   = date   if date   is not None else old_date
        new_amount = amount if amount is not None else old_amount
        new_source = source if source is not None else old_source
        new_note   = note   if note   is not None else old_note

        conn.execute(
            "UPDATE credits SET date = ?, amount = ?, source = ?, note = ? WHERE id = ?",
            (new_date, new_amount, new_source, new_note, credit_id)
        )

    month = new_date[:7]
    total_income   = _total_credits_month(month)
    total_budgeted = _total_budgeted_month(month)
    total_spent    = _total_spent_month(month)

    result = {
        'status': 'ok',
        'message': f"Credit {credit_id} updated.",
        'updated': {
            'id': credit_id, 'date': new_date,
            'amount': new_amount, 'source': new_source, 'note': new_note,
        },
        'month_summary': {
            'total_income':   round(total_income, 2),
            'total_budgeted': round(total_budgeted, 2),
            'total_spent':    round(total_spent, 2),
            'unallocated':    round(total_income - total_budgeted, 2),
            'net_savings':    round(total_income - total_spent, 2),
        }
    }

    if total_budgeted > total_income > 0:
        result['alert'] = (
            f"⚠️  Your budgets ({total_budgeted:,.0f}) now exceed your updated income "
            f"({total_income:,.0f}). Consider adjusting your budgets."
        )
    return result


@mcp.tool()
def delete_credit(credit_id: int) -> dict:
    """
    Delete a credit / income entry by its ID.

    Args:
        credit_id: The ID of the credit entry to remove (use list_credits to find it).
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM credits WHERE id = ?", (credit_id,))
    return {'status': 'ok', 'message': f"Credit entry {credit_id} deleted."}


# ─────────────────────────────────────────────
# MCP Tools — Budgets
# ─────────────────────────────────────────────

@mcp.tool()
def set_budget(category: str, limit_amount: float, month: str = '') -> dict:
    """
    Set (or update) a monthly spending budget for a category.

    The system will warn you if your total budgets across all categories exceed
    your logged income for the month.

    Args:
        category:     The expense category to budget (e.g. 'food', 'transport').
        limit_amount: Monthly spending cap (e.g. 10000).
        month:        Target month in YYYY-MM format. Defaults to the current month.

    Example prompts:
        "Set my food budget to 10,000 for this month."
        "Update my transport budget to 5,000."
    """
    if not month:
        month = _current_month()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO budgets (category, month, limit_amount) VALUES (?, ?, ?) "
            "ON CONFLICT(category, month) DO UPDATE SET limit_amount = excluded.limit_amount",
            (category, month, limit_amount)
        )

    total_income = _total_credits_month(month)
    total_budgeted = _total_budgeted_month(month)

    result = {
        'status': 'ok',
        'message': f"Budget set: {category} → {limit_amount:,.0f} for {month}",
        'category': category,
        'month': month,
        'limit_amount': limit_amount,
    }

    if total_income > 0:
        unallocated = total_income - total_budgeted
        result['income_context'] = {
            'total_income': round(total_income, 2),
            'total_budgeted': round(total_budgeted, 2),
            'unallocated': round(unallocated, 2),
        }
        if total_budgeted > total_income:
            result['alert'] = (
                f"⚠️  Total budgets ({total_budgeted:,.0f}) now exceed your "
                f"income ({total_income:,.0f}) by {total_budgeted - total_income:,.0f}. "
                f"Consider reducing some budgets."
            )
    else:
        result['tip'] = (
            "💡 No income logged for this month yet. "
            "Use add_credit to log your salary or other income so the system "
            "can verify your budgets fit within your earnings."
        )

    return result


@mcp.tool()
def list_budgets(month: str = '') -> list:
    """
    List all budgets for a given month, with live spent / remaining amounts,
    and income context so you can see how budgets relate to what you earned.

    Args:
        month: Month in YYYY-MM format. Defaults to the current month.
    """
    if not month:
        month = _current_month()

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT category, limit_amount FROM budgets WHERE month = ? ORDER BY category",
            (month,)
        )
        rows = cur.fetchall()

    result = []
    for category, limit_amount in rows:
        spent = _spent_this_month(category, month)
        remaining = limit_amount - spent
        pct_used = (spent / limit_amount * 100) if limit_amount > 0 else 0

        if pct_used >= 100:
            status = "🚨 EXCEEDED"
        elif pct_used >= 80:
            status = "⚠️  WARNING"
        else:
            status = "✅ OK"

        result.append({
            'category': category,
            'month': month,
            'budget': limit_amount,
            'spent': round(spent, 2),
            'remaining': round(remaining, 2),
            'percent_used': round(pct_used, 1),
            'status': status,
        })

    return result


@mcp.tool()
def check_budget_alerts(month: str = '') -> list:
    """
    Check all budgets for the given month and return any active alerts.
    Includes category over-budget alerts, 80% warnings, weekly-pace alerts,
    and income vs budget health checks.

    Args:
        month: Month in YYYY-MM format. Defaults to the current month.

    Call this when the user asks "Am I on track?" or "Any budget warnings?".
    """
    if not month:
        month = _current_month()

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT category, limit_amount FROM budgets WHERE month = ?",
            (month,)
        )
        rows = cur.fetchall()

    alerts = []
    for category, limit_amount in rows:
        spent = _spent_this_month(category, month)
        a = _build_alert(category, spent, limit_amount)
        if a:
            alerts.append(a)
        p = _weekly_pace_alert(category, month, limit_amount)
        if p:
            alerts.append(p)

    # Income-level cross checks
    alerts.extend(_credit_health_alerts(month))

    if not alerts:
        alerts = [f"✅ All budgets for {month} are within limits."]

    return alerts


@mcp.tool()
def delete_budget(category: str, month: str = '') -> dict:
    """
    Remove the budget for a category in a given month.

    Args:
        category: The category whose budget should be removed.
        month:    Month in YYYY-MM format. Defaults to the current month.
    """
    if not month:
        month = _current_month()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM budgets WHERE category = ? AND month = ?", (category, month))

    return {'status': 'ok', 'message': f"Budget removed for {category} in {month}."}


# ─────────────────────────────────────────────
# MCP Tools — Monthly Financial Overview
# ─────────────────────────────────────────────

@mcp.tool()
def monthly_overview(month: str = '') -> dict:
    """
    Full financial snapshot for a month: income, total budgeted, total spent,
    net savings, unallocated income, and all active budget statuses.

    This is the single tool to call when the user asks:
    "How am I doing this month?" / "What's my financial summary?" /
    "How much have I spent vs earned?"

    Args:
        month: Month in YYYY-MM format. Defaults to the current month.
    """
    if not month:
        month = _current_month()

    total_income = _total_credits_month(month)
    total_budgeted = _total_budgeted_month(month)
    total_spent = _total_spent_month(month)
    unallocated = total_income - total_budgeted
    net_savings = total_income - total_spent
    savings_pct = (net_savings / total_income * 100) if total_income > 0 else 0

    # Per-category budget breakdown
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT category, limit_amount FROM budgets WHERE month = ? ORDER BY category",
            (month,)
        )
        budget_rows = cur.fetchall()

        # Credit breakdown by source
        start, end = _month_range(month)
        cur2 = conn.execute(
            "SELECT source, SUM(amount) FROM credits "
            "WHERE date BETWEEN ? AND ? GROUP BY source ORDER BY source",
            (start, end)
        )
        income_by_source = [{'source': r[0], 'amount': r[1]} for r in cur2.fetchall()]

    category_details = []
    for category, limit_amount in budget_rows:
        spent = _spent_this_month(category, month)
        remaining = limit_amount - spent
        pct = (spent / limit_amount * 100) if limit_amount > 0 else 0
        status = "🚨 EXCEEDED" if pct >= 100 else ("⚠️  WARNING" if pct >= 80 else "✅ OK")
        category_details.append({
            'category': category,
            'budget': limit_amount,
            'spent': round(spent, 2),
            'remaining': round(remaining, 2),
            'percent_used': round(pct, 1),
            'status': status,
        })

    alerts = []
    if total_income > 0 and total_budgeted > total_income:
        alerts.append(f"🚨 Budgets ({total_budgeted:,.0f}) exceed income ({total_income:,.0f})")
    if total_income > 0 and total_spent > total_income:
        alerts.append(f"🚨 Spending ({total_spent:,.0f}) exceeds income ({total_income:,.0f})")
    if total_income > 0 and 0 <= savings_pct < 10:
        alerts.append(f"⚠️  Saving only {savings_pct:.1f}% of income")

    return {
        'month': month,
        'income': {
            'total': round(total_income, 2),
            'by_source': income_by_source,
        },
        'budgets': {
            'total_allocated': round(total_budgeted, 2),
            'unallocated': round(unallocated, 2),
        },
        'spending': {
            'total_spent': round(total_spent, 2),
            'net_savings': round(net_savings, 2),
            'savings_percent': round(savings_pct, 1),
        },
        'category_breakdown': category_details,
        'alerts': alerts if alerts else ["✅ Finances look healthy this month."],
    }


# ─────────────────────────────────────────────
# MCP Resources
# ─────────────────────────────────────────────

@mcp.resource('expense://categories', mime_type='application/json')
def categories() -> str:
    with open(CATEGORIES_PATH, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return json.dumps(data)
        except json.JSONDecodeError:
            return "{}"


# ─────────────────────────────────────────────
# Run MCP Server
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
