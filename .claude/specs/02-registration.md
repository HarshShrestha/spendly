# Spec: Registration

## Overview
This feature implements the user registration process, allowing new users to create an account by providing their name, email, and password. This is a foundational step in the Spendly roadmap, enabling personalized expense tracking and data persistence for individual users.

## Depends on
Step 1 (Database Setup)

## Routes
- `POST /register` — Handle new user registration — public

## Database changes
No database changes. (The `users` table already exists with required columns: `id`, `name`, `email`, `password_hash`, `created_at`).

## Templates
- **Create:** None
- **Modify:** `templates/register.html` — Update to include a proper `<form>` that posts to `/register`.

## Files to change
- `app.py` — Implement the `POST /register` route logic.
- `database/db.py` — Add a helper function `create_user(name, email, password_hash)` to insert a new user.
- `templates/register.html` — Ensure the registration form is correctly set up.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`

## Definition of done
- [ ] User can submit the registration form with valid data.
- [ ] New user is correctly inserted into the `users` table with a hashed password.
- [ ] Duplicate email registrations are handled gracefully (e.g., using `abort(400)` or a flash message).
- [ ] After successful registration, the user is redirected to the login page.
- [ ] Registration fails if required fields are missing.
