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


def get_user_by_email(email):
    """
    Retrieves a user from the database by their email address.
    Returns the user row or None if not found.
    """
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()


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


def get_user_profile(user_id):
    """
    Retrieves user profile information.
    """
    with get_db() as conn:
        user = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if user:
            # Simple formatting for join date (e.g., '2024-01-15 10:00:00' -> 'January 2024')
            # created_at is stored as a string in ISO format
            import datetime
            dt = datetime.datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S')
            return {
                "name": user['name'],
                "email": user['email'],
                "join_date": dt.strftime('%B %Y')
            }
        return None


def get_user_stats(user_id):
    """
    Calculates spending statistics for the user.
    """
    with get_db() as conn:
        # Total spent and count
        stats_row = conn.execute(
            "SELECT SUM(amount) as total, COUNT(id) as count FROM expenses WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        total_spent = stats_row['total'] or 0.0
        count = stats_row['count'] or 0

        # Top category
        top_cat_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,)
        ).fetchone()

        return {
            "total_spent": f"₹{total_spent:,.2f}",
            "transaction_count": count,
            "top_category": top_cat_row['category'] if top_cat_row else "None"
        }


def get_recent_transactions(user_id, limit=5):
    """
    Retrieves most recent transactions.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()

        return [
            {
                "date": row['date'],
                "description": row['description'],
                "category": row['category'],
                "amount": f"₹{row['amount']:,.2f}"
            }
            for row in rows
        ]


def get_category_breakdown(user_id):
    """
    Retrieves spending breakdown by category.
    """
    with get_db() as conn:
        # Get total first for percentage
        total_spent = conn.execute(
            "SELECT SUM(amount) as total FROM expenses WHERE user_id = ?",
            (user_id,)
        ).fetchone()['total'] or 0.0

        rows = conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,)
        ).fetchall()

        breakdown = []
        for row in rows:
            amt = row['total']
            perc = (amt / total_spent * 100) if total_spent > 0 else 0
            breakdown.append({
                "category": row['category'],
                "amount": f"₹{amt:,.2f}",
                "percentage": round(perc)
            })
        return breakdown


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
