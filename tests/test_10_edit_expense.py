import pytest
import sqlite3
from app import app as flask_app, EXPENSE_CATEGORIES
from database.db import init_db, add_expense

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': ':memory:',
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    # Patch database.db to use the in-memory database for the duration of the test
    import database.db
    original_get_db = database.db.get_db

    # We need a single connection for :memory: to persist across calls in one test
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")

    def mocked_get_db():
        return connection

    database.db.get_db = mocked_get_db

    with flask_app.app_context():
        init_db()
        yield flask_app

    database.db.get_db = original_get_db
    connection.close()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    client.post('/register', data={'name': 'testuser', 'email': 'testuser@example.com', 'password': 'testpass'})
    client.post('/login', data={'email': 'testuser@example.com', 'password': 'testpass'})
    return client

class TestEditExpense:

    def test_edit_expense_get_success(self, auth_client):
        """Happy Path: Accessing the edit page for an owned expense renders the form."""
        # Create an expense for the logged-in user
        with flask_app.app_context():
            # We need the user_id. Since we just logged in, it's in the session.
            # But we can't easily access session here. Let's find the user in DB.
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users WHERE email = 'testuser@example.com'").fetchone()
            user_id = user['id']
            expense_id = add_expense(user_id, 50.0, "Food", "2023-10-01", "Original Lunch")

        response = auth_client.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 200
        assert b'Original Lunch' in response.data
        assert b'50' in response.data
        assert b'Food' in response.data

    def test_edit_expense_post_success(self, auth_client):
        """Happy Path: Successfully updating an expense record."""
        with flask_app.app_context():
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users WHERE email = 'testuser@example.com'").fetchone()
            user_id = user['id']
            expense_id = add_expense(user_id, 50.0, "Food", "2023-10-01", "Original Lunch")

        # Update data
        updated_data = {
            'amount': '75.50',
            'category': 'Shopping',
            'date': '2023-10-02',
            'description': 'Updated Shopping Trip'
        }
        response = auth_client.post(f'/expenses/{expense_id}/edit', data=updated_data, follow_redirects=True)

        assert response.status_code == 200
        # Should redirect to profile
        assert b'Profile' in response.data or '/profile' in response.request.path

        # Verify DB side effects
        with flask_app.app_context():
            import database.db
            conn = database.db.get_db()
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row['amount'] == 75.50
            assert row['category'] == 'Shopping'
            assert row['date'] == '2023-10-02'
            assert row['description'] == 'Updated Shopping Trip'

    def test_edit_expense_unauthenticated(self, client):
        """Auth Guard: Unauthenticated users are redirected to login."""
        response = client.get('/expenses/1/edit')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_edit_expense_not_owned(self, auth_client):
        """Authorization: Users cannot edit expenses belonging to others."""
        with flask_app.app_context():
            import database.db
            conn = database.db.get_db()
            # User 1 is the auth_client user. Let's create User 2.
            from werkzeug.security import generate_password_hash
            database.db.create_user("Other User", "other@example.com", generate_password_hash("pass"))
            other_user = conn.execute("SELECT id FROM users WHERE email = 'other@example.com'").fetchone()
            other_user_id = other_user['id']
            other_expense_id = add_expense(other_user_id, 100.0, "Bills", "2023-10-01", "Other Person's Bill")

        # Try to access edit page
        response = auth_client.get(f'/expenses/{other_expense_id}/edit')
        assert response.status_code == 404

        # Try to POST update
        response = auth_client.post(f'/expenses/{other_expense_id}/edit', data={'amount': '200'}, follow_redirects=True)
        assert response.status_code == 404

    def test_edit_expense_non_existent(self, auth_client):
        """Authorization: Editing a non-existent expense returns 404."""
        response = auth_client.get('/expenses/9999/edit')
        assert response.status_code == 404

    @pytest.mark.parametrize("invalid_data, expected_error", [
        ({'amount': '-10', 'category': 'Food', 'date': '2023-10-01', 'description': 'test'}, "Amount must be a positive number"),
        ({'amount': '0', 'category': 'Food', 'date': '2023-10-01', 'description': 'test'}, "Amount must be a positive number"),
        ({'amount': 'abc', 'category': 'Food', 'date': '2023-10-01', 'description': 'test'}, "Amount must be a numeric value"),
        ({'amount': '10', 'category': 'InvalidCat', 'date': '2023-10-01', 'description': 'test'}, "Invalid category selected"),
        ({'amount': '10', 'category': 'Food', 'date': 'not-a-date', 'description': 'test'}, "Invalid date format"),
        ({'amount': '10', 'category': 'Food', 'date': '2023-10-01', 'description': 'a' * 201}, "Description must be 200 characters or less"),
        ({'amount': '', 'category': 'Food', 'date': '2023-10-01', 'description': 'test'}, "Amount is required"),
        ({'amount': '10', 'category': 'Food', 'date': '', 'description': 'test'}, "Date is required"),
    ])
    def test_edit_expense_validation_errors(self, auth_client, invalid_data, expected_error):
        """Validation: Ensuring invalid inputs return appropriate error messages."""
        with flask_app.app_context():
            import database.db
            conn = database.db.get_db()
            user = conn.execute("SELECT id FROM users WHERE email = 'testuser@example.com'").fetchone()
            user_id = user['id']
            expense_id = add_expense(user_id, 50.0, "Food", "2023-10-01", "Original")

        response = auth_client.post(f'/expenses/{expense_id}/edit', data=invalid_data)
        assert response.status_code == 200
        assert expected_error.encode() in response.data

        # Verify DB was NOT updated
        with flask_app.app_context():
            import database.db
            conn = database.db.get_db()
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row['amount'] == 50.0
