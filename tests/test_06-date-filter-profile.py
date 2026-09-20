import pytest
from app import app as flask_app
from database.db import init_db
import sqlite3
from datetime import datetime, timedelta

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': 'test_spendly.db',
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    # Monkeypatch DB_PATH to use the test database file
    import database.db
    database.db.DB_PATH = 'test_spendly.db'

    with flask_app.app_context():
        init_db()
        # Ensure a clean state for every test
        with database.db.get_db() as conn:
            conn.execute("DELETE FROM expenses")
            conn.execute("DELETE FROM users")
            conn.commit()
        yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already registered and logged in."""
    client.post('/register', data={'name': 'Test User', 'email': 'test@example.com', 'password': 'password123'})
    client.post('/login', data={'email': 'test@example.com', 'password': 'password123'})
    return client

@pytest.fixture
def seed_data(app):
    """Seeds the in-memory database with specific dates for filtering tests."""
    import database.db
    with database.db.get_db() as conn:
        # Get the logged in user ID (we know it's 1 because of auth_client)
        user_id = 1

        today = datetime.now()

        # Data for this month
        this_month_date = today.strftime('%Y-%m-%d')

        # Data for 2 months ago (should be in 3m and 6m, but not 'this month')
        two_months_ago = (today - timedelta(days=60)).strftime('%Y-%m-%d')

        # Data for 5 months ago (should be in 6m, but not 3m)
        five_months_ago = (today - timedelta(days=150)).strftime('%Y-%m-%d')

        # Data for 1 year ago (should be in none of the presets except 'all time')
        one_year_ago = (today - timedelta(days=365)).strftime('%Y-%m-%d')

        expenses = [
            (user_id, 100.0, 'Food', this_month_date, 'Current Month Lunch'),
            (user_id, 200.0, 'Transport', two_months_ago, 'Old Travel'),
            (user_id, 300.0, 'Bills', five_months_ago, 'Old Bill'),
            (user_id, 400.0, 'Shopping', one_year_ago, 'Ancient Purchase'),
        ]

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()

class TestDateFilterProfile:

    def test_profile_unauthenticated_redirect(self, client):
        """Unauthenticated access to /profile should redirect to login."""
        response = client.get('/profile', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_profile_unfiltered_view(self, auth_client, seed_data):
        """Accessing /profile without params should show all data."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        # Total: 100+200+300+400 = 1000
        assert b'\xe2\x82\xb91,000.00' in response.data
        assert b'4' in response.data # Transaction count
        assert b'Ancient Purchase' in response.data

    def test_profile_valid_custom_range(self, auth_client, seed_data):
        """Filtering with a valid custom date range."""
        # We want only the items from 2 months ago and 5 months ago
        # Range: 6 months ago to 1 month ago
        today = datetime.now()
        date_from = (today - timedelta(days=180)).strftime('%Y-%m-%d')
        date_to = (today - timedelta(days=30)).strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200
        # Should contain 200 (2m ago) and 300 (5m ago) = 500
        assert b'\xe2\x82\xb9500.00' in response.data
        assert b'Old Travel' in response.data
        assert b'Old Bill' in response.data
        assert b'Current Month Lunch' not in response.data
        assert b'Ancient Purchase' not in response.data

    def test_profile_boundary_inclusive(self, auth_client, seed_data):
        """Ensure the filter is inclusive of the start and end dates."""
        today = datetime.now()
        date_str = today.strftime('%Y-%m-%d')

        # Range only covering today
        response = auth_client.get(f'/profile?date_from={date_str}&date_to={date_str}')

        assert b'\xe2\x82\xb9100.00' in response.data
        assert b'Current Month Lunch' in response.data

    def test_profile_preset_this_month(self, auth_client, seed_data):
        """Simulate 'This Month' preset."""
        today = datetime.now()
        date_from = today.replace(day=1).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert b'\xe2\x82\xb9100.00' in response.data
        assert b'Current Month Lunch' in response.data
        assert b'Old Travel' not in response.data

    def test_profile_preset_last_3m(self, auth_client, seed_data):
        """Simulate 'Last 3 Months' preset."""
        today = datetime.now()
        date_from = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        # Should have this month (100) and 2 months ago (200) = 300
        assert b'\xe2\x82\xb9300.00' in response.data
        assert b'Current Month Lunch' in response.data
        assert b'Old Travel' in response.data
        assert b'Old Bill' not in response.data

    def test_profile_preset_last_6m(self, auth_client, seed_data):
        """Simulate 'Last 6 Months' preset."""
        today = datetime.now()
        date_from = (today - timedelta(days=180)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        # Should have this month (100), 2 months ago (200), and 5 months ago (300) = 600
        assert b'\xe2\x82\xb9600.00' in response.data
        assert b'Old Bill' in response.data
        assert b'Ancient Purchase' not in response.data

    def test_profile_empty_range(self, auth_client, seed_data):
        """Date range with no expenses should show zeros."""
        # Future dates
        date_from = "2099-01-01"
        date_to = "2099-01-31"

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200
        assert b'\xe2\x82\xb90.00' in response.data
        assert b'0' in response.data # count
        assert b'None' in response.data # top category

    def test_profile_invalid_date_order(self, auth_client, seed_data):
        """date_from > date_to should flash error and fall back to unfiltered."""
        response = auth_client.get('/profile?date_from=2024-12-31&date_to=2024-01-01')

        # Should flash error
        assert b'Start date must be before end date.' in response.data
        # Should fall back to unfiltered (Total 1000)
        assert b'\xe2\x82\xb91,000.00' in response.data

    def test_profile_malformed_date(self, auth_client, seed_data):
        """Malformed date strings should silently fall back to unfiltered."""
        response = auth_client.get('/profile?date_from=not-a-date&date_to=2024-01-01')

        assert response.status_code == 200
        # Should fall back to unfiltered (Total 1000)
        assert b'\xe2\x82\xb91,000.00' in response.data
