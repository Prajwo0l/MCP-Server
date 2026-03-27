# 💰 Expense MCP Server

A lightweight, local-first **Model Context Protocol (MCP) server** for tracking personal and business expenses. It exposes tools that any MCP-compatible AI client (such as Claude Desktop) can call to add, list, and summarize expenses — all stored in a local SQLite database — with optional **Google Calendar integration**, a **Budget + Alerts** system, and a **Credit (Income) system** that grounds your budgets in what you actually earn.

---

## ✨ Features

- 📥 **Add expenses** with date, amount, category, optional subcategory, and notes
- 📅 **Sync to Google Calendar** — log expenses as calendar events after user approval
- 📋 **List expenses** filtered by date range
- 📊 **Summarize expenses** by category over any date range
- 💳 **Credit system** — log your income (salary, freelance, rental, bonus, etc.) so the system knows your real spendable pool for each month
- 💰 **Budget + Alerts** — set monthly spending limits per category, verified against your income:
  - ⚠️ Warning when you hit 80% of a category budget
  - 🚨 Alert when you exceed a category budget
  - 💡 Pace alert when spending faster than usual
  - 🚨 Alert when total budgets exceed total income
  - 🚨 Alert when total spending exceeds total income
  - ⚠️ Low savings rate warning
- 📅 **Monthly overview** — one-shot financial snapshot: income vs budgeted vs spent vs saved
- 🗂️ **20 built-in categories** with detailed subcategories
- 💾 **Local SQLite storage** — your data never leaves your machine
- 🔐 **Human-in-the-loop (HITL)** — calendar events only created after explicit user confirmation
- ⚡ Built with [FastMCP](https://github.com/jlowin/fastmcp) for a clean, minimal setup

---

## 📋 Requirements

| Requirement | Version |
|---|---|
| Python | ≥ 3.13 |
| [uv](https://github.com/astral-sh/uv) | Latest |
| fastmcp | < 3.0.0 |

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/expense-mcp-server.git
cd expense-mcp-server
```

### 2. Install Dependencies

```bash
uv sync
```

> **Don't have `uv`?** Install it first:
> ```bash
> pip install uv
> ```

---

## 🔑 Google Calendar Setup (Optional)

To enable the `add_to_calendar` tool, you need a Google Cloud OAuth2 credentials file.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create/select a project
2. Enable the **Google Calendar API**
3. Create **OAuth 2.0 credentials** (Desktop App type) and download as `credentials.json` in the project root
4. On first run, a browser window will open for authorisation; a `token.json` is saved automatically

> ⚠️ Keep `credentials.json` and `token.json` out of version control (already in `.gitignore`).

---

## 🔧 Configuration with Claude Desktop

Add this to your `claude_desktop_config.json`:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**macOS/Linux:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ExpenseTracker": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YourName\\Desktop\\Expense MCP Server",
        "run",
        "main.py"
      ]
    }
  }
}
```

Restart Claude Desktop after saving. `ExpenseTracker` will appear as a connected tool.

---

## 🛠️ Available Tools

### Expense Tools

#### `add_expense`
Add a new expense. Automatically checks active budgets and income health, returning alerts if any thresholds are crossed.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | `string` | ✅ | Date in `YYYY-MM-DD` format |
| `amount` | `float` | ✅ | Expense amount |
| `category` | `string` | ✅ | Main category (e.g. `food`, `transport`) |
| `subcategory` | `string` | ❌ | Optional subcategory |
| `note` | `string` | ❌ | Optional note |

#### `add_to_calendar`
Create a Google Calendar event for an expense (only after user approval).

#### `list_expenses`
List all expenses between two dates.

#### `edit_expense`

Correct a mistake in an existing expense — wrong amount, wrong category, wrong date. Only the fields you provide are updated.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `expense_id` | `int` | ✅ | ID of the expense to edit (get it from `list_expenses`) |
| `date` | `string` | ❌ | Corrected date `YYYY-MM-DD` |
| `amount` | `float` | ❌ | Corrected amount |
| `category` | `string` | ❌ | Corrected category |
| `subcategory` | `string` | ❌ | Corrected subcategory |
| `note` | `string` | ❌ | Updated note |

After editing, budget alerts are re-evaluated automatically.

**Example prompts:**
> *"The grocery amount should be 950 not 1200 — fix expense 5."*
> *"Change the category of expense 3 to transport."*

#### `delete_expense`
Delete an expense entry by ID.

#### `summarize`
Summarize spending by category over a date range.

---

### 💳 Credit (Income) Tools

#### `add_credit`

Log income received for the month — the foundation of the budget system. Once income is logged, the system can verify that your budgets don't exceed what you earned, and track real net savings.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | `string` | ✅ | Date income was received, `YYYY-MM-DD` |
| `amount` | `float` | ✅ | Amount received |
| `source` | `string` | ✅ | Label: `salary`, `freelance`, `rental`, `bonus`, `interest`, `gift`, `refund`, `other` |
| `note` | `string` | ❌ | Optional description |

**Example prompts:**
> *"I got my salary of 75,000 today."*
> *"Log a 15,000 freelance payment received on March 25."*
> *"Add rental income of 8,000 for this month."*

**Returns:**
```json
{
  "status": "ok",
  "id": 3,
  "date": "2026-03-01",
  "amount": 75000,
  "source": "salary",
  "month_summary": {
    "total_income": 75000,
    "total_budgeted": 42000,
    "total_spent": 18500,
    "unallocated": 33000,
    "net_savings": 56500
  }
}
```

#### `list_credits`
List all income entries for a given month.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `month` | `string` | ❌ | Month in `YYYY-MM` format. Defaults to current month |

#### `edit_credit`

Edit an existing income entry — correct a wrong amount, change the source, or fix the date. Only the fields you pass are updated; everything else stays unchanged.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `credit_id` | `int` | ✅ | ID of the entry to edit (get it from `list_credits`) |
| `amount` | `float` | ❌ | Corrected amount |
| `source` | `string` | ❌ | Corrected source label |
| `date` | `string` | ❌ | Corrected date `YYYY-MM-DD` |
| `note` | `string` | ❌ | Updated note |

After editing, the response includes a refreshed `month_summary` and an alert if your budgets now exceed your updated income.

**Example prompts:**
> *"My salary was actually 80,000 not 75,000 — fix credit 1."*
> *"Change the source of credit 2 to freelance."*

#### `delete_credit`
Delete an income entry by ID (use `list_credits` to find the ID).

---

### 💰 Budget Tools

#### `set_budget`

Set (or update) a monthly spending cap for a category. If income has been logged, the response includes an `income_context` block showing how much of your income is allocated vs unallocated. If your total budgets exceed income, an alert is returned immediately.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `category` | `string` | ✅ | Category to budget |
| `limit_amount` | `float` | ✅ | Monthly spending cap |
| `month` | `string` | ❌ | `YYYY-MM`. Defaults to current month |

**Returns:**
```json
{
  "status": "ok",
  "message": "Budget set: food → 10,000 for 2026-03",
  "income_context": {
    "total_income": 75000,
    "total_budgeted": 42000,
    "unallocated": 33000
  }
}
```

#### `list_budgets`
List all budgets for a month with live spent / remaining / % used and status.

#### `check_budget_alerts`
Return all active alerts for a month — category budgets AND income health.

#### `delete_budget`
Remove a budget for a category + month.

---

### 📅 Monthly Overview Tool

#### `monthly_overview`

A complete one-shot financial snapshot for any month. Combines income, budgets, and spending into one structured response.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `month` | `string` | ❌ | `YYYY-MM`. Defaults to current month |

**Call this when the user asks:**
> *"How am I doing this month?"*
> *"Give me a financial summary."*
> *"What's my income vs spending?"*

**Returns:**
```json
{
  "month": "2026-03",
  "income": {
    "total": 83000,
    "by_source": [
      { "source": "freelance", "amount": 8000 },
      { "source": "salary", "amount": 75000 }
    ]
  },
  "budgets": {
    "total_allocated": 42000,
    "unallocated": 41000
  },
  "spending": {
    "total_spent": 18500,
    "net_savings": 64500,
    "savings_percent": 77.7
  },
  "category_breakdown": [
    { "category": "food", "budget": 10000, "spent": 8500, "remaining": 1500, "percent_used": 85.0, "status": "⚠️  WARNING" },
    { "category": "transport", "budget": 5000, "spent": 2100, "remaining": 2900, "percent_used": 42.0, "status": "✅ OK" }
  ],
  "alerts": ["✅ Finances look healthy this month."]
}
```

---

## 🚨 Alert Reference

| Alert | Trigger |
|---|---|
| ⚠️ Category Warning | Spent ≥ 80% of a category budget |
| 🚨 Category Exceeded | Spent ≥ 100% of a category budget |
| 💡 Pace Alert | Spending rate implies month-end overage (> 20% ahead of proportional pace) |
| 🚨 Over-Allocated | Total budgets > total income |
| 🚨 Spending > Income | Total spending exceeds total income for the month |
| ⚠️ Low Savings | Saving less than 10% of income |

Alerts fire **automatically inside `add_expense`** responses when relevant. Call `check_budget_alerts` or `monthly_overview` any time for a full status snapshot.

---

## 📁 Project Structure

```
expense-mcp-server/
├── main.py              # MCP server — all tools and resources
├── categories.json      # Supported categories and subcategories
├── credentials.json     # Google OAuth2 credentials (not committed)
├── token.json           # Google OAuth2 token (auto-generated, not committed)
├── expenses.db          # SQLite database (auto-created on first run)
├── pyproject.toml       # Project metadata and dependencies
├── uv.lock              # Locked dependency versions
└── README.md            # This file
```

---

## 🗄️ Database Schema

```sql
-- Expense records
CREATE TABLE expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,        -- YYYY-MM-DD
    amount      REAL NOT NULL,
    category    TEXT NOT NULL,
    subcategory TEXT DEFAULT NULL,
    note        TEXT DEFAULT NULL
);

-- Monthly category budgets
CREATE TABLE budgets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category     TEXT NOT NULL,
    month        TEXT NOT NULL,       -- YYYY-MM
    limit_amount REAL NOT NULL,
    UNIQUE(category, month)
);

-- Income / credit entries
CREATE TABLE credits (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    date   TEXT NOT NULL,             -- YYYY-MM-DD
    amount REAL NOT NULL,
    source TEXT NOT NULL,             -- e.g. 'salary', 'freelance'
    note   TEXT DEFAULT NULL
);
```

All tables are created automatically on first run.

---

## 💡 Recommended Workflow

```
1. Start of month:
   → add_credit "salary 75000"         # log your income first
   → set_budget food 10000             # allocate budgets (system checks vs income)
   → set_budget transport 5000
   → set_budget subscriptions 3000
   → ...

2. Throughout the month:
   → add_expense (alerts fire if nearing limits)
   → check_budget_alerts               # quick status check any time

3. End of month review:
   → monthly_overview                  # full income vs spending vs savings snapshot
```

---

## 🗂️ Categories

| Category | Example Subcategories |
|---|---|
| `food` | groceries, dining_out, coffee_tea, delivery_fees |
| `transport` | fuel, public_transport, cab_ride_hailing, parking |
| `housing` | rent, repairs_service, furnishing |
| `utilities` | electricity, internet_broadband, mobile_phone |
| `health` | medicines, doctor_consultation, fitness_gym |
| `education` | books, courses, online_subscriptions, exam_fees |
| `entertainment` | movies_events, streaming_subscriptions, outing |
| `shopping` | clothing, electronics_gadgets, home_decor |
| `travel` | flights, hotels, train_bus, visa_passport |
| `investments` | mutual_funds, stocks, crypto, gold |
| `business` | hosting_domains, contractor_payments, marketing_ads |
| `subscriptions` | saas_tools, cloud_ai, music_video |
| `personal_care` | salon_spa, grooming, cosmetics |
| `family_kids` | school_fees, daycare, toys_games |
| `gifts_donations` | gifts_personal, charity_donation, festivals |
| `finance_fees` | bank_charges, interest, brokerage |
| `taxes` | income_tax, gst, professional_tax |
| `home` | household_supplies, cleaning_supplies, kitchenware |
| `pet` | food, vet, grooming, supplies |
| `misc` | uncategorized, other |

---

## 💡 Example Conversations

```
"I got my salary of 75,000 today."
→ Logs credit, shows total income & unallocated amount

"Set my food budget to 10,000."
→ Sets budget, shows how much income is still unallocated

"Log 1,200 for groceries today."
→ Saves expense, fires ⚠️ warning if food budget is near limit

"Am I on track this month?"
→ check_budget_alerts: returns all warnings + income health

"Give me a full financial summary."
→ monthly_overview: income, budgets, spending, savings in one shot
```

---

## 🤝 Contributing

Pull requests welcome! Ideas:
- Recurring budget copy (auto-roll budgets to next month)
- Multi-currency support
- Export to CSV / Excel
- Savings goal tracking
- Timezone config via environment variable

---

## 📄 License

Open source. See [LICENSE](LICENSE) for details.

---

*Built with [FastMCP](https://github.com/jlowin/fastmcp) · SQLite · Google Calendar · Local-first privacy*
