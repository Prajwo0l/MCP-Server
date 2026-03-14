from fastmcp import FastMCP
import os
import sqlite3

DB_PATH=os.path.join(os.path.dirname(__file__),'expenses.db')


mcp=FastMCP("ExpenseTracker")

def init_db():
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
    print("Database initialized successfully!")

init_db()

@mcp.tool()
def add_expense(date,amount,category,subcategory='',note=''):
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            'INSERT INTO expenses(date,amount,category,subcategory,note) VALUES (?,?,?,?,?)',
            (date,amount,category,subcategory,note)
        )
        return {'status':'ok','id':cur.lastrowid}


@mcp.tool()
def list_expenses():
    '''List all expnese entries from the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute('SELECT id,date,amount,category,subcategory,note FROM expenses ORDER BY id ASC')
        cols=[d[0]for d in cur.description]
        return [dict(zip(cols,r) for r in cur.fetchall())]
    

if __name__=='__main__':
    mcp.run()