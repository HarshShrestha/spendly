from flask import Flask, render_template, request, redirect, url_for, session, flash
from database.db import init_db, seed_db, create_user, get_user_by_email, get_user_profile, get_user_stats, get_recent_transactions, get_category_breakdown, add_expense, delete_expense
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "dev-secret-key-for-spendly"

EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

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


def _get_date_filter_params():
    """Helper to validate date filters and calculate presets."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    validated_from = None
    validated_to = None

    if date_from and date_to:
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")

            if date_from > date_to:
                flash("Start date must be before end date.")
            else:
                validated_from = date_from
                validated_to = date_to
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.")

    today = datetime.now().date()
    presets = {
        "this_month": (today.replace(day=1).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")),
        "last_3m": ((today - timedelta(days=90)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")),
        "last_6m": ((today - timedelta(days=180)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")),
    }

    return validated_from, validated_to, presets


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    user = get_user_profile(user_id)
    if not user:
        return redirect(url_for("login")) # User no longer exists

    validated_from, validated_to, presets = _get_date_filter_params()

    stats = get_user_stats(user_id, validated_from, validated_to)
    transactions = get_recent_transactions(user_id, date_from=validated_from, date_to=validated_to)
    categories = get_category_breakdown(user_id, validated_from, validated_to)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=validated_from,
        date_to=validated_to,
        presets=presets
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login", next="/expenses/add"))

    user_id = session["user_id"]

    if request.method == "POST":
        # Get form data
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_str = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip() or None

        # Validation
        error = None
        form_data = {
            "amount": amount_str,
            "category": category,
            "date": date_str,
            "description": description or ""
        }

        # Validate amount
        if not amount_str:
            error = "Amount is required"
        else:
            try:
                amount = float(amount_str)
                if amount <= 0:
                    error = "Amount must be a positive number"
            except ValueError:
                error = "Amount must be a numeric value"

        # Validate category
        if not error and category not in EXPENSE_CATEGORIES:
            error = "Invalid category selected"

        # Validate date
        if not error:
            if not date_str:
                error = "Date is required"
            else:
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    error = "Invalid date format. Please use YYYY-MM-DD."

        # Validate description length
        if not error and description and len(description) > 200:
            error = "Description must be 200 characters or less"

        if error:
            return render_template("add_expense.html", error=error, form_data=form_data, categories=EXPENSE_CATEGORIES)

        # All valid - insert expense
        try:
            from database.db import add_expense as db_add_expense
            db_add_expense(user_id, amount, category, date_str, description)
        except sqlite3.Error:
            return render_template("add_expense.html", error="Failed to save expense. Please try again.", form_data=form_data, categories=EXPENSE_CATEGORIES)

        return redirect(url_for("profile"))

    # GET request - render form with today's date as default
    today = datetime.now().date().strftime("%Y-%m-%d")
    return render_template("add_expense.html", categories=EXPENSE_CATEGORIES, default_date=today)


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def handle_delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))

    user_id = session["user_id"]

    if delete_expense(id, user_id):
        flash("Expense deleted successfully", "success")
    else:
        flash("Expense not found or you do not have permission to delete it", "error")

    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
