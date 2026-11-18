
import sqlite3

def connect():
    return sqlite3.connect("expenses.db")

def create_table():
    con = connect()

    # Transactions table
    con.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount REAL,
            description TEXT
        )
    """)

    # Budgets table
    con.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT UNIQUE,
            amount REAL
        )
    """)

    con.commit()
    con.close()

create_table()
