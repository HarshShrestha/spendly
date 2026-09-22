# Spec: Edit Expense

## Overview
This feature allows users to modify existing expense records. It provides a way to correct mistakes in amount, category, date, or description, ensuring that the user's financial tracking remains accurate over time. This is a key part of the expense management lifecycle, following the addition and preceding the deletion of records.

## Depends on
- Step 07: Add Expense (for the form logic and categories)
- Step 01: Database Setup (for the expenses table)

## Routes
- `GET /expenses/<int:id>/edit` — Renders the edit form pre-filled with existing expense data — logged-in
- `POST /expenses/<int:id>/edit` — Validates and updates the expense record in the database — logged-in

## Database changes
No database changes.

## Templates
- **Create:** `templates/edit_expense.html` (similar to `add_expense.html` but pre-filled)
- **Modify:** No existing templates need modification.

## Files to change
- `app.py` — Implement the GET and POST handlers for the edit route.
- `database/db.py` — Add a helper function `update_expense(expense_id, user_id, amount, category, date, description)` to handle the update logic.

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Ensure a user can only edit their own expenses by verifying `user_id` during the update.

## Definition of done
- [ ] Navigating to `/expenses/<id>/edit` for a valid expense belonging to the logged-in user renders a form with correct current values.
- [ ] Navigating to `/expenses/<id>/edit` for an expense that doesn't exist or belongs to another user results in a 404 or redirect.
- [ ] Submitting the edit form with valid data updates the record in the database and redirects to the profile page.
- [ ] Submitting the edit form with invalid data (e.g., negative amount, invalid date) shows appropriate error messages and retains the input.
- [ ] The update is reflected immediately on the profile page.
