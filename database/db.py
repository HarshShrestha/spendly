import sqlite3
from werkzeug.security import generate_password_hash
from datetime import date

DB_PATH = "spendly.db"

def get_db():
    """
    Returns a connection to the SQLite database with row_factory set to Row
    and foreign key constraints enabled.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_user(name, email, password_hash):
    """
    Creates a new user in the database.
    Returns the ID of the newly created user.
    """
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
        return cur.lastrowid


def init_db():
    """
    Initializes the database by creating the users and expenses tables.
    """
    with get_db() as conn:
        # Create users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Create expenses table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        conn.commit()

def seed_db():
    """
    Populates the database with sample data for development if it's empty.
    """
    with get_db() as conn:
        # Check if users table already contains data
        cur = conn.execute("SELECT 1 FROM users LIMIT 1")
        if cur.fetchone():
            return

        # Insert demo user
        hashed_pw = generate_password_hash("demo123")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", hashed_pw)
        )
        user_id = cur.lastrowid

        # Sample expenses data
        # Categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other
        today = date.today()
        year = today.year
        month = today.month

        expenses = [
            (user_id, 15.50, 'Food', f"{year}-{month:02d}-01", 'Lunch at Cafe'),
            (user_id, 30.00, 'Transport', f"{year}-{month:02d}-03", 'Weekly Pass'),
            (user_id, 120.00, 'Bills', f"{year}-{month:02d}-05", 'Internet Bill'),
            (user_id, 45.00, 'Health', f"{year}-{month:02d}-08", 'Pharmacy'),
            (user_id, 60.00, 'Entertainment', f"{year}-{month:02d}-12", 'Cinema'),
            (user_id, 85.20, 'Shopping', f"{year}-{month:02d}-15", 'New Shirt'),
            (user_id, 10.00, 'Other', f"{year}-{month:02d}-17", 'Misc'),
            (user_id, 22.00, 'Food', f"{year}-{month:02d}-18", 'Dinner'),
        ]

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
