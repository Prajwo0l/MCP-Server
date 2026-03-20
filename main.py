from fastmcp import FastMCP
import os
import sqlite3
import json
import datetime  # keep this
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service


def create_calendar_event(date, amount, category, note):
    service = get_calendar_service()

    event = {
        'summary': f"💸 {category}: {amount}",
        'description': note or '',
        'start': {
            'date': date,  # YYYY-MM-DD format
            'timeZone': 'Asia/Kathmandu',  # replace with your timezone
        },
        'end': {
            'date': date,
            'timeZone': 'Asia/Kathmandu',
        },
    }

    service.events().insert(calendarId='primary', body=event).execute()




# Paths
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'expenses.db')
CATEGORIES_PATH = os.path.join(BASE_DIR, 'categories.json')

# Initialize MCP
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
    """Add a new expense"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            'INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)',
            (date, amount, category, subcategory, note)
        )

    # Add to Google Calendar
    try:
        create_calendar_event(date, amount, category, note)
    except Exception as e:
        print("Calendar error:", e)

    return {'status': 'ok', 'id': cur.lastrowid}

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