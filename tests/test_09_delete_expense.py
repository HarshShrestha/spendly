import pytest
import sqlite3
from app import app as flask_app
from database.db import init_db, add_expense, get_user_stats

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': ':memory:',  # isolated in-memory DB per test
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    with flask_app.app_context():
        # Since database.db.get_db() uses a hardcoded DB_PATH,
        # we must override it to use a shared in-memory connection for the duration of the test.
        import database.db as db
        original_get_db = db.get_db

        # Create a shared in-memory connection
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")

        def mocked_get_db():
            return conn

        db.get_db = mocked_get_db
        init_db()
        yield flask_app

        db.get_db = original_get_db

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    # Register a user
    client.post('/register', data={'name': 'Test User', 'email': 'test@test.com', 'password': 'testpass'})
    # Login
    client.post('/login', data={'email': 'test@test.com', 'password': 'testpass'})
    return client

class TestDeleteExpense:

    def test_delete_own_expense_success(self, auth_client):
        """Happy path: User deletes their own expense."""
        # Setup: Add an expense
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']

        expense_id = add_expense(user_id, 100.0, 'Food', '2023-01-01', 'Test Meal')

        # Action: Delete the expense
        response = auth_client.post(f'/expenses/{expense_id}/delete', follow_redirects=True)

        # Assertions
        assert response.status_code == 200
        assert b"Expense deleted successfully" in response.data

        # DB Verification
        with auth_client.application.app_context():
            import database.db as db
            conn = db.get_db()
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row is None, "Expense should have been deleted from DB"

    def test_delete_expense_unauthenticated(self, client):
        """Auth guard: Unlogged user cannot delete."""
        # Action: Attempt to delete an expense
        response = client.post('/expenses/1/delete', follow_redirects=False)

        # Assertions
        assert response.status_code == 302
        assert '/login' in response.location

    def test_delete_other_user_expense(self, auth_client):
        """Ownership security: User cannot delete another user's expense."""
        # Setup: Two users
        with auth_client.session_transaction() as sess:
            user_a_id = sess['user_id']

        # Create User B
        import database.db as db
        from werkzeug.security import generate_password_hash
        user_b_id = db.create_user("User B", "userb@test.com", generate_password_hash("passb"))

        # User B has an expense
        expense_id = add_expense(user_b_id, 50.0, 'Transport', '2023-01-01', 'User B Bus')

        # Action: User A attempts to delete User B's expense
        response = auth_client.post(f'/expenses/{expense_id}/delete', follow_redirects=True)

        # Assertions
        assert response.status_code == 200
        assert b"Expense not found or you do not have permission to delete it" in response.data

        # DB Verification: Expense should still exist
        with auth_client.application.app_context():
            conn = db.get_db()
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row is not None, "Other user's expense should NOT have been deleted"

    def test_delete_non_existent_expense(self, auth_client):
        """Edge case: Delete an expense ID that doesn't exist."""
        # Action: Delete ID 9999
        response = auth_client.post('/expenses/9999/delete', follow_redirects=True)

        # Assertions
        assert response.status_code == 200
        assert b"Expense not found or you do not have permission to delete it" in response.data

    def test_delete_updates_stats(self, auth_client):
        """Side effects: Stats update after deletion."""
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']

        # Setup: Add two expenses
        add_expense(user_id, 100.0, 'Food', '2023-01-01', 'Meal 1')
        expense_id_2 = add_expense(user_id, 50.0, 'Food', '2023-01-02', 'Meal 2')

        # Initial Stats
        stats_before = get_user_stats(user_id)
        assert stats_before['transaction_count'] == 2

        # Action: Delete one
        auth_client.post(f'/expenses/{expense_id_2}/delete')

        # Stats After
        stats_after = get_user_stats(user_id)
        assert stats_after['transaction_count'] == 1
        # Total spent should be 100.00 (formatted)
        assert "100.00" in stats_after['total_spent']
