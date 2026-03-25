# 💰 Expense MCP Server

A lightweight, local-first **Model Context Protocol (MCP) server** for tracking personal and business expenses. It exposes tools that any MCP-compatible AI client (such as Claude Desktop) can call to add, list, and summarize expenses — all stored in a local SQLite database — with optional **Google Calendar integration** to log expenses as calendar events.

---

## ✨ Features

- 📥 **Add expenses** with date, amount, category, optional subcategory, and notes
- 📅 **Sync to Google Calendar** — log expenses as calendar events after user approval
- 📋 **List expenses** filtered by date range
- 📊 **Summarize expenses** by category over any date range
- 🗂️ **20 built-in categories** with detailed subcategories (food, transport, health, travel, etc.)
- 💾 **Local SQLite storage** — your data never leaves your machine
- 🔐 **Human-in-the-loop (HITL)** — calendar events are only created after explicit user confirmation
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

## 🔑 Google Calendar Setup (Optional)

To enable the `add_to_calendar` tool, you need a Google Cloud OAuth2 credentials file.

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**
4. Search for **Google Calendar API** and enable it

### 2. Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Choose **Desktop App** as the application type
4. Download the credentials file and save it as `credentials.json` in the project root

### 3. Authenticate

On first run, the server will open a browser window asking you to authorise access to your Google Calendar. After approving, a `token.json` file will be saved automatically for future use.

> ⚠️ Keep `credentials.json` and `token.json` out of version control. Add them to `.gitignore`.

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
> **Windows example:** `C:\\Users\\YourName\\Desktop\\expense-mcp-server`

After saving the config, **restart Claude Desktop**. You should see `ExpenseTracker` listed as a connected tool.

---

## 🛠️ Available Tools

### `add_expense`

Add a new expense entry to the SQLite database.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | `string` | ✅ | Date in `YYYY-MM-DD` format |
| `amount` | `float` | ✅ | Expense amount (e.g. `49.99`) |
| `category` | `string` | ✅ | Main category (see [Categories](#-categories)) |
| `subcategory` | `string` | ❌ | Subcategory within the main category |
| `note` | `string` | ❌ | Optional note or description |

> This tool **only saves to the database**. It does not create a calendar event. To sync to Google Calendar, use `add_to_calendar` separately after confirming with the user.

**Example prompt to Claude:**
> *"Add an expense of $12.50 for coffee on 2025-07-10."*

**Returns:**
```json
{ "status": "ok", "id": 42, "date": "2025-07-10", "amount": 12.50, "category": "food", "note": "Morning coffee" }
```

---

### `add_to_calendar`

Create a Google Calendar event for an expense. 

> ⚠️ **Only call this tool after the user has explicitly approved adding the expense to their calendar.** This is intentional — the HITL design ensures no calendar events are created without user confirmation.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | `string` | ✅ | Date in `YYYY-MM-DD` format |
| `amount` | `float` | ✅ | Expense amount |
| `category` | `string` | ✅ | Expense category (used as the event title) |
| `note` | `string` | ❌ | Optional note (added as event description) |

The event is created as an all-day event on the given date, titled `💸 {category}: {amount}`, in the `Asia/Kathmandu` timezone.

**Example prompt to Claude:**
> *"Add that coffee expense to my calendar too."*

**Returns:**
```json
{ "status": "ok", "message": "Calendar event created: food 12.5 on 2025-07-10" }
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

**Example prompts to Claude:**
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

A built-in MCP resource that returns the full list of supported categories and subcategories as a JSON object. AI clients can read this resource to know which category values are valid when calling `add_expense`.

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
├── credentials.json     # Google OAuth2 credentials (not committed)
├── token.json           # Google OAuth2 token — auto-generated on first auth (not committed)
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

> *"Add that to my Google Calendar too."* ← triggers `add_to_calendar` after your approval

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request for:

- New categories or subcategories
- Additional MCP tools (e.g., delete, edit, export to CSV)
- Multi-currency support
- Budget tracking features
- Timezone configuration via environment variable

---

## 📄 License

This project is open source. See [LICENSE](LICENSE) for details.

---

*Built with [FastMCP](https://github.com/jlowin/fastmcp) · Powered by SQLite · Google Calendar Integration · Designed for local-first privacy*