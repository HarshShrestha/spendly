from flask import Flask, render_template, request, redirect, url_for, session
from database.db import init_db, seed_db, create_user, get_user_by_email
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "dev-secret-key-for-spendly"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required")

        hashed_pw = generate_password_hash(password)

        try:
            create_user(name, email, hashed_pw)
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Email already registered")

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password")

        if not email or not password:
            return render_template("login.html", error="Email and password are required")

        user = get_user_by_email(email)

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            return redirect(url_for("profile"))

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded data for UI-first implementation
    user = {
        "name": "Harsh Shrestha",
        "email": "harsh@example.com",
        "join_date": "January 2024"
    }

    stats = {
        "total_spent": "₹12,450.00",
        "transaction_count": 42,
        "top_category": "Food"
    }

    recent_transactions = [
        {"date": "2024-09-18", "description": "Dinner at Taj", "category": "Food", "amount": "₹1,200.00"},
        {"date": "2024-09-17", "description": "Uber Ride", "category": "Transport", "amount": "₹350.00"},
        {"date": "2024-09-15", "description": "Netflix Subscription", "category": "Entertainment", "amount": "₹499.00"},
        {"date": "2024-09-12", "description": "Grocery Shopping", "category": "Shopping", "amount": "₹2,100.00"},
        {"date": "2024-09-10", "description": "Pharmacy", "category": "Health", "amount": "₹600.00"},
    ]

    category_breakdown = [
        {"category": "Food", "amount": "₹4,500.00", "percentage": 36},
        {"category": "Shopping", "amount": "₹3,200.00", "percentage": 25},
        {"category": "Transport", "amount": "₹2,100.00", "percentage": 17},
        {"category": "Entertainment", "amount": "₹1,500.00", "percentage": 12},
        {"category": "Other", "amount": "₹1,150.00", "percentage": 10},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=recent_transactions,
        categories=category_breakdown
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
