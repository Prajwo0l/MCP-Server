from fastmcp import FastMCP
import os
import sqlite3
import json
import datetime  # keep this
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

    service = build('calendar', 'v3', credentials=creds)
    return service


def create_calendar_event(date, amount, category, note):
    service = get_calendar_service()

    event = {
        'summary': f"💸 {category}: {amount}",
        'description': note or '',
        'start': {
            'date': date,  
            'timeZone': 'Asia/Kathmandu', 
        },
        'end': {
            'date': date,
            'timeZone': 'Asia/Kathmandu',
        },
    }

    service.events().insert(calendarId='primary', body=event).execute()





DB_PATH = os.path.join(BASE_DIR, 'expenses.db')
CATEGORIES_PATH = os.path.join(BASE_DIR, 'categories.json')

mcp = FastMCP("ExpenseTracker")

# -----------------------------
# Database Initialization
# -----------------------------
def init_db():
    """Create the expenses table if it doesn't exist"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT NULL,
                note TEXT DEFAULT NULL
            )
        """)

init_db()

# -----------------------------
# MCP Tools
# -----------------------------
@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = '', note: str = '') -> dict:
    """
    Add a new expense to the tracker (saves to database only).
    The Google Calendar event will be created separately after user approval.

    Args:
        date: The date of the expense in YYYY-MM-DD format (e.g. '2026-03-20')
        amount: The amount spent as a number (e.g. 1200)
        category: The category of the expense (e.g. 'Food', 'Transport', 'Laptop')
        subcategory: Optional subcategory (e.g. 'Groceries')
        note: Optional note or description about the expense

    Always extract date, amount and category from the user message before calling this tool.
    If the user does not provide a date, use today's date in YYYY-MM-DD format.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            'INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)',
            (date, amount, category, subcategory, note)
        )
        expense_id = cur.lastrowid
    return {'status': 'ok', 'id': expense_id, 'date': date, 'amount': amount, 'category': category, 'note': note}


@mcp.tool()
def add_to_calendar(date: str, amount: float, category: str, note: str = '') -> dict:
    """
    Create a Google Calendar event for an expense.
    Only call this tool AFTER the user has explicitly approved adding to calendar.

    Args:
        date: The date in YYYY-MM-DD format
        amount: The expense amount
        category: The expense category
        note: Optional note
    """
    try:
        create_calendar_event(date, amount, category, note)
        return {'status': 'ok', 'message': f'Calendar event created: {category} {amount} on {date}'}
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}

@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> list:
    """List expenses between start_date and end_date"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize(start_date: str, end_date: str, category: str = None) -> list:
    """Summarize expenses by category"""
    with sqlite3.connect(DB_PATH) as conn:
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " GROUP BY category ORDER BY category ASC"

        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

# -----------------------------
# MCP Resources
# -----------------------------
@mcp.resource('expense://categories', mime_type='application/json')
def categories() -> str:
    """Return categories.json contents as valid JSON string"""
    with open(CATEGORIES_PATH, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return json.dumps(data)
        except json.JSONDecodeError:
            return "{}"

# -----------------------------
# Run MCP Server
# -----------------------------
if __name__ == "__main__":
    mcp.run()