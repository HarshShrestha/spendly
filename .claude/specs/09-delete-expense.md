# Spec: Delete Expense

## Overview
This feature allows users to delete their existing expense records. It is a critical part of the expense management lifecycle, enabling users to correct mistakes or remove irrelevant entries from their spending history.

## Depends on
- Step 07: Add Expense (for existing expenses to delete)
- Step 04: Profile (where the delete action will be initiated)

## Routes
- `GET /expenses/<int:id>/delete` — Deletes a specific expense record if it belongs to the logged-in user — logged-in

## Database changes
No database changes.

## Templates
- **Modify:** `profile.html` — Add a delete button/link for each transaction in the recent transactions list.

## Files to change
- `app.py`
- `database/db.py`
- `templates/profile.html`

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Verify the expense belongs to the current `user_id` before deleting to prevent unauthorized deletions.

## Definition of done
- [ ] A "Delete" button/link appears next to each expense in the profile page.
- [ ] Clicking "Delete" removes the expense from the database.
- [ ] The user is redirected back to the profile page with a success message.
- [ ] Attempting to delete an expense that doesn't exist or belongs to another user results in a 404 or error message.
- [ ] The "Total Spent" and "Transaction Count" stats update immediately after deletion.
