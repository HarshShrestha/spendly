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


def _apply_date_filter(query, params, date_from, date_to):
    """Internal helper to append date range filter to a query."""
    if date_from and date_to:
        query += " AND date BETWEEN ? AND ?"
        params.extend([date_from, date_to])
    return query, params


def get_user_stats(user_id: int, date_from: str = None, date_to: str = None):
    """
    Calculates spending statistics for the user, optionally filtered by date range.
    """
    with get_db() as conn:
        # Total spent and count
        query = "SELECT SUM(amount) as total, COUNT(id) as count FROM expenses WHERE user_id = ?"
        params = [user_id]

        query, params = _apply_date_filter(query, params, date_from, date_to)
        stats_row = conn.execute(query, params).fetchone()

        total_spent = stats_row['total'] or 0.0
        count = stats_row['count'] or 0

        # Top category
        cat_query = "SELECT category FROM expenses WHERE user_id = ?"
        cat_params = [user_id]

        cat_query, cat_params = _apply_date_filter(cat_query, cat_params, date_from, date_to)
        cat_query += " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1"

        top_cat_row = conn.execute(cat_query, cat_params).fetchone()

        return {
            "total_spent": f"₹{total_spent:,.2f}",
            "transaction_count": count,
            "top_category": top_cat_row['category'] if top_cat_row else "None"
        }


def get_recent_transactions(user_id, limit=5, date_from=None, date_to=None):
    """
    Retrieves most recent transactions, optionally filtered by date range.
    """
    with get_db() as conn:
        query = "SELECT id, date, description, category, amount FROM expenses WHERE user_id = ?"
        params = [user_id]

        query, params = _apply_date_filter(query, params, date_from, date_to)
        query += " ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": row['id'],
                "date": row['date'],
                "description": row['description'],
                "category": row['category'],
                "amount": f"₹{row['amount']:,.2f}"
            }
            for row in rows
        ]


def get_category_breakdown(user_id: int, date_from: str = None, date_to: str = None):
    """
    Retrieves spending breakdown by category, optionally filtered by date range.
    """
    with get_db() as conn:
        # Get total first for percentage
        total_query = "SELECT SUM(amount) as total FROM expenses WHERE user_id = ?"
        total_params = [user_id]

        total_query, total_params = _apply_date_filter(total_query, total_params, date_from, date_to)
        total_spent = conn.execute(total_query, total_params).fetchone()['total'] or 0.0

        # Get breakdown
        break_query = "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?"
        break_params = [user_id]

        break_query, break_params = _apply_date_filter(break_query, break_params, date_from, date_to)
        break_query += " GROUP BY category ORDER BY total DESC"

        rows = conn.execute(break_query, break_params).fetchall()

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

def add_expense(user_id: int, amount: float, category: str, date: str, description: str = None):
    """
    Inserts a new expense record for the given user.
    Returns the ID of the newly created expense.
    """
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description)
        )
        conn.commit()
        return cur.lastrowid


def delete_expense(expense_id: int, user_id: int) -> bool:
    """
    Deletes an expense record if it belongs to the specified user.
    Returns True if deletion was successful, False otherwise.
    """
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


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
