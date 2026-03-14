from fastmcp import FastMCP
import os
import sqlite3
import json

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