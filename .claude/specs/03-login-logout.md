# Spec: Login and Logout

## Overview
This feature implements the authentication flow for Spendly, allowing users to securely log into their accounts and log out. It establishes the session management mechanism that will be used by all subsequent protected routes (like the profile and expense management pages).

## Depends on
- 01 Database Setup
- 02 Registration

## Routes
- `GET /login` — Renders the login page — public
- `POST /login` — Validates credentials and starts a session — public
- `GET /logout` — Ends the user session and redirects to landing — logged-in

## Database changes
No database changes.

## Templates
- **Modify:** `login.html` — Update to include a form that posts to `/login`.
- **Modify:** `base.html` — Add conditional navigation links (e.g., "Login" vs "Logout" and "Profile") based on the user's authentication status.

## Files to change
- `app.py` — Implement login and logout logic.
- `database/db.py` — Add a helper function to fetch a user by email.
- `templates/base.html` — Update navigation.
- `templates/login.html` — Update form.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use Flask `session` for user state management

## Definition of done
- [ ] User can log in with valid email and password.
- [ ] User is redirected to the profile page (or landing) after successful login.
- [ ] User sees an error message on the login page for invalid credentials.
- [ ] User cannot access protected routes without logging in.
- [ ] Navigation in `base.html` updates correctly (Login $\rightarrow$ Logout/Profile) after login.
- [ ] User is successfully logged out via `/logout` and redirected to landing.