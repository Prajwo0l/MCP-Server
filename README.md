# 💰 Expense MCP Server

A lightweight, local-first **Model Context Protocol (MCP) server** for tracking personal and business expenses. It exposes tools that any MCP-compatible AI client (such as Claude Desktop) can call to add, list, and summarize expenses — all stored in a local SQLite database.

---

## ✨ Features

- 📥 **Add expenses** with date, amount, category, optional subcategory, and notes
- 📋 **List expenses** filtered by date range
- 📊 **Summarize expenses** by category over any date range
- 🗂️ **20 built-in categories** with detailed subcategories (food, transport, health, travel, etc.)
- 💾 **Local SQLite storage** — your data never leaves your machine
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

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management.

```bash
uv sync
```

> **Don't have `uv`?** Install it first:
> ```bash
> pip install uv
> ```

---

## 🔧 Configuration with Claude Desktop

To use this server with **Claude Desktop**, add it to your `claude_desktop_config.json`:

### macOS / Linux

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Windows

```
%APPDATA%\Claude\claude_desktop_config.json
```

### Config Entry

```json
{
  "mcpServers": {
    "ExpenseTracker": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/expense-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```

> ⚠️ Replace `/absolute/path/to/expense-mcp-server` with the actual full path to the project folder on your machine.
>
> **Windows example:** `C:\\Users\\YourName\\Desktop\\Expense MCP Server`

After saving the config, **restart Claude Desktop**. You should see `ExpenseTracker` listed as a connected tool.

---

## 🛠️ Available Tools

### `add_expense`

Add a new expense entry to the database.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | `string` | ✅ | Date in `YYYY-MM-DD` format |
| `amount` | `float` | ✅ | Expense amount (e.g. `49.99`) |
| `category` | `string` | ✅ | Main category (see [Categories](#-categories)) |
| `subcategory` | `string` | ❌ | Subcategory within the main category |
| `note` | `string` | ❌ | Optional note or description |

**Example prompt to Claude:**
> *"Add an expense of $12.50 for coffee on 2025-07-10."*

**Returns:**
```json
{ "status": "ok", "id": 42 }
```

---

### `list_expenses`

Retrieve all expenses within a date range.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start_date` | `string` | ✅ | Start date in `YYYY-MM-DD` format |
| `end_date` | `string` | ✅ | End date in `YYYY-MM-DD` format |

**Example prompt to Claude:**
> *"Show me all my expenses from July 1 to July 31, 2025."*

**Returns:**
```json
[
  {
    "id": 1,
    "date": "2025-07-10",
    "amount": 12.50,
    "category": "food",
    "subcategory": "coffee_tea",
    "note": "Morning coffee"
  }
]
```

---

### `summarize`

Get a category-level summary of spending over a date range.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start_date` | `string` | ✅ | Start date in `YYYY-MM-DD` format |
| `end_date` | `string` | ✅ | End date in `YYYY-MM-DD` format |
| `category` | `string` | ❌ | Filter to a specific category only |

**Example prompt to Claude:**
> *"Summarize my spending for this month."*
> *"How much did I spend on food in June 2025?"*

**Returns:**
```json
[
  { "category": "food", "total_amount": 340.75 },
  { "category": "transport", "total_amount": 120.00 }
]
```

---

## 📦 Available Resource

### `expense://categories`

A built-in MCP resource that returns the full list of supported categories and subcategories as a JSON object. AI clients can read this to know which category values are valid when adding expenses.

---

## 🗂️ Categories

The server includes **20 top-level categories**, each with detailed subcategories:

| Category | Example Subcategories |
|---|---|
| `food` | groceries, dining_out, coffee_tea, delivery_fees |
| `transport` | fuel, public_transport, cab_ride_hailing, parking |
| `housing` | rent, repairs_service, furnishing, maintenance_hoa |
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

> See `categories.json` for the complete list of subcategories.

---

## 📁 Project Structure

```
expense-mcp-server/
├── main.py              # MCP server — tools and resources
├── categories.json      # All supported categories and subcategories
├── expenses.db          # SQLite database (auto-created on first run)
├── pyproject.toml       # Project metadata and dependencies
├── uv.lock              # Locked dependency versions
└── README.md            # This file
```

---

## 🗄️ Database Schema

Expenses are stored in a single SQLite table:

```sql
CREATE TABLE expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,        -- YYYY-MM-DD
    amount      REAL    NOT NULL,        -- Numeric value
    category    TEXT    NOT NULL,        -- Top-level category
    subcategory TEXT    DEFAULT NULL,    -- Optional subcategory
    note        TEXT    DEFAULT NULL     -- Optional free-text note
);
```

The database file (`expenses.db`) is created automatically in the project directory on first run.

---

## 💡 Example Conversations with Claude

Once connected, you can talk to Claude naturally:

> *"Log $45 for groceries today."*

> *"What did I spend last week?"*

> *"How much have I spent on subscriptions this month?"*

> *"Give me a full breakdown of my July expenses."*

> *"Add a $200 expense for flights on 2025-08-01 under travel."*

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request for:

- New categories or subcategories
- Additional MCP tools (e.g., delete, edit, export to CSV)
- Multi-currency support
- Budget tracking features

---

## 📄 License

This project is open source. See [LICENSE](LICENSE) for details.

---

*Built with [FastMCP](https://github.com/jlowin/fastmcp) · Powered by SQLite · Designed for local-first privacy*
