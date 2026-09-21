import pytest
from app import app as flask_app
from database.db import init_db
import database.db

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': 'test_spendly.db',
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    # Monkeypatch DB_PATH to use the test database file
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

class TestAddExpense:

    # --- Auth Guards ---

    def test_add_expense_get_unauthenticated_redirects(self, client):
        """Unauthenticated GET /expenses/add should redirect to login."""
        response = client.get('/expenses/add', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_add_expense_post_unauthenticated_redirects(self, client):
        """Unauthenticated POST /expenses/add should redirect to login."""
        response = client.post('/expenses/add', data={'amount': '10.0'}, follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    # --- UI Verification ---

    def test_add_expense_form_renders_correctly(self, auth_client):
        """Authenticated user should see the add expense form with all requirements."""
        response = auth_client.get('/expenses/add')
        assert response.status_code == 200

        # Verify form structure
        assert b'<form' in response.data
        assert b'method="POST"' in response.data

        # Verify fields
        assert b'name="amount"' in response.data
        assert b'name="category"' in response.data
        assert b'name="date"' in response.data
        assert b'name="description"' in response.data

        # Verify categories
        categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
        for cat in categories:
            assert cat.encode() in response.data

    # --- Happy Paths ---

    def test_add_expense_success_full_data(self, auth_client):
        """Adding a valid expense should redirect to profile and save to DB."""
        payload = {
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch at Cafe'
        }
        response = auth_client.post('/expenses/add', data=payload, follow_redirects=False)

        # Verify Redirect
        assert response.status_code == 302
        assert '/profile' in response.location

        # Verify DB Insertion
        with database.db.get_db() as conn:
            row = conn.execute(
                "SELECT amount, category, date, description FROM expenses WHERE description = ?",
                ('Lunch at Cafe',)
            ).fetchone()
            assert row is not None
            assert float(row[0]) == 50.0
            assert row[1] == 'Food'
            assert row[2] == '2026-03-20'
            assert row[3] == 'Lunch at Cafe'

    def test_add_expense_success_no_description(self, auth_client):
        """Adding an expense without a description should save description as NULL."""
        payload = {
            'amount': '20.0',
            'category': 'Transport',
            'date': '2026-03-21',
            'description': '' # Blank
        }
        response = auth_client.post('/expenses/add', data=payload, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.location

        with database.db.get_db() as conn:
            row = conn.execute(
                "SELECT description FROM expenses WHERE amount = ?",
                (20.0,)
            ).fetchone()
            assert row[0] is None  # Should be NULL in DB

    # --- Validation Errors ---

    @pytest.mark.parametrize("payload, expected_error", [
        # Missing amount
        ({'category': 'Food', 'date': '2026-03-20', 'description': 'Test'}, b'amount'),
        # Zero amount
        ({'amount': '0', 'category': 'Food', 'date': '2026-03-20', 'description': 'Test'}, b'positive'),
        # Negative amount
        ({'amount': '-10', 'category': 'Food', 'date': '2026-03-20', 'description': 'Test'}, b'positive'),
        # Non-numeric amount
        ({'amount': 'abc', 'category': 'Food', 'date': '2026-03-20', 'description': 'Test'}, b'numeric'),
        # Invalid category
        ({'amount': '10', 'category': 'Luxury', 'date': '2026-03-20', 'description': 'Test'}, b'category'),
        # Invalid date format
        ({'amount': '10', 'category': 'Food', 'date': '20-03-2026', 'description': 'Test'}, b'date'),
        # Empty date
        ({'amount': '10', 'category': 'Food', 'date': '', 'description': 'Test'}, b'date'),
    ])
    def test_add_expense_validation_failures(self, auth_client, payload, expected_error):
        """Various invalid inputs should re-render the form with an error message."""
        response = auth_client.post('/expenses/add', data=payload)

        assert response.status_code == 200
        assert expected_error in response.data.lower()

        # Verify that provided values are retained in the form
        for key, value in payload.items():
            if value:
                # Only verify retention for fields that are NOT the category
                # since the <select> might not show the invalid option
                if key != 'category':
                    assert value.encode() in response.data
