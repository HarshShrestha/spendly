# Spec: Backend Routes for Profile Page

## Overview
This feature replaces the hardcoded data in the `/profile` route with real data fetched from the SQLite database. It involves creating several database helper functions to retrieve user profile information, calculate spending statistics, and fetch transaction history and category breakdowns for the currently logged-in user.

## Depends on
- Step 4: Profile Page (UI implementation)
- Step 1: Database setup (schema must exist)

## Routes
- `GET /profile` — Modify existing route to fetch data from database using `session['user_id']` — logged-in

## Database changes
No database changes. The `users` and `expenses` tables already support all required queries.

## Templates
No templates to create. The `templates/profile.html` created in Step 4 will be used.

## Files to change
- `database/db.py`: Add helper functions for profile data.
- `app.py`: Update the `/profile` route to call these helpers.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Use `get_db()` for all connections
- All DB logic must reside in `database/db.py`
- Route functions must only handle the coordination between DB helpers and template rendering

## Definition of done
- [ ] Visiting `/profile` while logged in displays the actual name and email of the authenticated user.
- [ ] "Total Spent" correctly reflects the sum of all expenses for the logged-in user.
- [ ] "Transaction Count" correctly reflects the number of expenses for the logged-in user.
- [ ] "Top Category" correctly reflects the category with the highest total spend for the logged-in user.
- [ ] "Recent Transactions" table displays real records from the `expenses` table for the logged-in user, sorted by date descending.
- [ ] "Spending Breakdown" section correctly shows totals and percentages for each category the user has used.
- [ ] Visiting `/profile` while logged out still redirects to `/login`.

