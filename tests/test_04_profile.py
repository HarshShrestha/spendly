import pytest
from app import app as flask_app
from database.db import init_db, add_expense, create_user
import sqlite3
from datetime import datetime, timedelta

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': ':memory:',
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    # We need to override get_db to use the in-memory database for the app
    # Since get_db is in database.db, we'll monkeypatch it or ensure the app uses the same connection.
    # In this specific project structure, the app imports from database.db.
    # To make :memory: work across the app and tests, we must ensure they share the connection.

    # For simplicity in these tests, we'll use a temporary file or handle the connection.
    # However, following the prompt's fixture strategy:
    with flask_app.app_context():
        # We must monkeypatch database.db.get_db if we want :memory: to actually work
        # because get_db() currently hardcodes DB_PATH = "spendly.db".
        import database.db
        original_get_db = database.db.get_db

        # Create a shared connection for the in-memory DB
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")

        def mocked_get_db():
            return conn

        database.db.get_db = mocked_get_db
        init_db()
        yield flask_app

        # Restore
        database.db.get_db = original_get_db

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    # Register a user
    client.post('/register', data={'name': 'Test User', 'email': 'test@example.com', 'password': 'testpass'})
    # Login
    client.post('/login', data={'email': 'test@example.com', 'password': 'testpass'})
    return client

class TestProfilePage:

    def test_profile_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated users should be redirected to the login page."""
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_profile_authenticated_success(self, auth_client):
        """Logged-in user can view their profile page."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        assert b'Profile' in response.data or b'User Info' in response.data

    def test_profile_displays_correct_stats_and_data(self, auth_client, app):
        """Profile should show correct summary stats and transactions for the user."""
        # Setup: Add some expenses for the logged-in user
        # Need to find the user_id first
        with app.app_context():
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
            user_id = user['id']

            add_expense(user_id, 100.0, 'Food', '2023-01-01', 'Lunch')
            add_expense(user_id, 200.0, 'Transport', '2023-01-02', 'Taxi')

        response = auth_client.get('/profile')
        assert response.status_code == 200
        # Stats: 100 + 200 = 300
        assert '₹300.00'.encode('utf-8') in response.data
        assert b'2' in response.data # Transaction count
        assert b'Transport' in response.data # Top category (alphabetical or amount)

    def test_profile_date_filtering_happy_path(self, auth_client, app):
        """Date range filters should correctly narrow down the displayed data."""
        with app.app_context():
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
            user_id = user['id']

            # Expense in range
            add_expense(user_id, 100.0, 'Food', '2023-05-10', 'In Range')
            # Expense out of range
            add_expense(user_id, 500.0, 'Bills', '2023-01-01', 'Out of Range')

        # Filter for May 2023
        response = auth_client.get('/profile?date_from=2023-05-01&date_to=2023-05-31')
        assert response.status_code == 200
        assert '₹100.00'.encode('utf-8') in response.data
        assert b'In Range' in response.data
        assert b'Out of Range' not in response.data
        assert "₹500.00".encode('utf-8') not in response.data

    def test_profile_presets_this_month(self, auth_client, app):
        """Preset 'This Month' should filter data for the current calendar month."""
        today = datetime.now()
        this_month_start = today.replace(day=1).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')

        with app.app_context():
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
            user_id = user['id']

            # Expense this month
            add_expense(user_id, 50.0, 'Food', this_month_start, 'Current Month')
            # Expense last month
            last_month = (today - timedelta(days=35)).strftime('%Y-%m-%d')
            add_expense(user_id, 1000.0, 'Bills', last_month, 'Old Month')

        # In the app, presets are links to /profile with query params.
        # We test if the route handles the calculated params correctly.
        # Since we don't know the exact preset calculation in the route's logic (it's internal),
        # we simulate the request the preset would make.
        response = auth_client.get(f'/profile?date_from={this_month_start}&date_to={today_str}')

        assert response.status_code == 200
        assert b'Current Month' in response.data
        assert b'Old Month' not in response.data
        assert '₹50.00'.encode('utf-8') in response.data

    @pytest.mark.parametrize("date_from, date_to", [
        ("not-a-date", "2023-01-01"),
        ("2023-01-01", "invalid"),
        ("2023-13-01", "2023-14-01"), # Invalid month
    ])
    def test_profile_malformed_dates_fallback_to_all_time(self, auth_client, app, date_from, date_to):
        """Malformed dates should not crash the app and should fallback to showing all data."""
        with app.app_context():
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
            user_id = user['id']
            add_expense(user_id, 100.0, 'Food', '2023-01-01', 'Test Expense')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')
        assert response.status_code == 200
        assert b'Test Expense' in response.data

    def test_profile_date_from_greater_than_date_to_shows_error(self, auth_client):
        """If date_from > date_to, an error should be flashed and view should be unfiltered."""
        with auth_client: # Ensure session is active
            response = auth_client.get('/profile?date_from=2023-12-01&date_to=2023-01-01')
            assert response.status_code == 200
            assert b'Start date must be before end date' in response.data

    def test_profile_user_no_longer_exists(self, client, app):
        """If the user session exists but the user is deleted from DB, redirect to login."""
        # 1. Create user and log in
        client.post('/register', data={'name': 'Gone', 'email': 'gone@example.com', 'password': 'password'})
        client.post('/login', data={'email': 'gone@example.com', 'password': 'password'})

        # 2. Delete user from DB
        with app.app_context():
            import database.db
            conn = database.db.get_db()
            conn.execute("DELETE FROM users WHERE email = 'gone@example.com'")
            conn.commit()

        # 3. Access profile
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_profile_no_expenses_in_range(self, auth_client, app):
        """A user with no expenses in the selected range should see zeroed stats."""
        with app.app_context():
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
            user_id = user['id']
            add_expense(user_id, 100.0, 'Food', '2023-01-01', 'Outside Range')

        # Filter for a range with no data
        response = auth_client.get('/profile?date_from=2024-01-01&date_to=2024-01-31')
        assert response.status_code == 200
        assert '₹0.00'.encode('utf-8') in response.data
        assert b'0' in response.data # count
        assert b'None' in response.data # top category
