# Step 3 — Login and Logout: Implementation Plan

Source spec: `.claude/specs/03-login-and-logout.md`

## Context

Registration (Step 2) already signs users in on signup
(`session["user_id"] = user_id`), but there was no way to sign back in
afterward. `/login` only rendered the form (GET-only, no POST handler)
and `/logout` was a raw-string stub (`"Logout — coming in Step 3"`).
This plan implements a `POST /login` handler that verifies
email/password against the `users` table and establishes a session, a
real `/logout` that clears it, and a session-aware nav bar so "Sign
out" is actually reachable. Scope was intentionally narrow — no
`login_required` decorator, no flash messages, no CSRF, no
remember-me checkbox, no profile personalization; all explicitly out
of scope per the spec.

## Design

**Auth flow.** `/login` gained a POST branch mirroring `register()`'s
existing shape: pull `email`/`password` from `request.form`, look up
the user, validate, and either re-render with a generic error or
establish a session and redirect. `/logout` became a two-line route:
pop `user_id` from the session, redirect to `landing`. Both stayed in
`app.py`; no new files.

**Password verification location — `app.py`, not `db.py`.** The spec
left this as a judgment call between two acceptable shapes. Chosen
approach: `db.py` exposes only `get_user_by_email(email)` — a pure
data-access read, symmetrical with every other function in that file
(one SQL statement, returns data, no business logic). `app.py` calls
`check_password_hash(user["password_hash"], password)` directly,
importing `check_password_hash` from `werkzeug.security` itself.

Justification:
- `check_password_hash` is a pure function with zero DB access —
  importing it into `app.py` doesn't violate "only `db.py` touches
  `sqlite3`." That rule is about the `sqlite3` module/connections, not
  every werkzeug helper.
- Keeps `get_user_by_email` symmetrical with `create_user` and the
  rest of `db.py` — each function does exactly one SQL statement, no
  auth/business logic mixed in.
- Mirrors `register()`'s existing control flow: validation-and-branch
  entirely in `app.py`, `db.py` only ever hands back rows (or raises
  `IntegrityError`). Login's branching (no user / bad password /
  success) stays in the route function, same as register's.
- The alternative (a `verify_login()` wrapper in `db.py`) would just
  relocate one function call with no clarity gain, and would blur
  `db.py`'s single responsibility (data access) with auth logic.

**Session-aware nav.** `base.html`'s `nav-links` div is wrapped in
`{% if session.user_id %}...{% else %}...{% endif %}`. Flask's
`session` proxy is automatically available in Jinja (no context
processor needed). Logged-in state renders a single "Sign out" link
(`url_for('logout')`); logged-out state is the previous two-link
markup, untouched.

**How this satisfies the spec's constraints:**
- No inline `sqlite3` in `app.py` — the only new query
  (`SELECT * FROM users WHERE email = ?`) lives entirely in
  `get_user_by_email` in `db.py`.
- Parameterized query — `get_user_by_email` uses a `?` placeholder,
  matching every existing query in the file.
- `url_for`-only — `login.html`'s form action and the new "Sign out"
  nav link both use `url_for`, no hardcoded paths.
- Banner-comment sections preserved — `/logout` physically moved from
  the "Placeholder routes" banner block to the "Routes" banner block,
  same precedent as `/register` in Step 2.
- Generic error message — both failure branches (`user is None` and
  `check_password_hash` returns `False`) converge on one `error`
  string, so the template/user can't tell them apart.
- Persistent session — `session.permanent = True` is set only on the
  success path, alongside `session["user_id"] = ...`, before the
  redirect.
- Session-aware nav — handled entirely in Jinja via `session.user_id`,
  no new route or context processor required.

## Implementation

1. **`database/db.py`** — added `get_user_by_email(email)` after
   `create_user`, following its `get_db()` / `try/finally: conn.close()`
   pattern: `SELECT * FROM users WHERE email = ?` (parameterized),
   `.fetchone()`, returns a `sqlite3.Row` or `None`.
2. **`app.py`** — added `get_user_by_email` to the `database.db`
   import line.
3. **`app.py`** — added `from werkzeug.security import
   check_password_hash`.
4. **`app.py`** — `/login`: added `methods=["GET", "POST"]`; GET
   branch unchanged; POST branch reads `email`/`password`, calls
   `get_user_by_email`, on failure re-renders with `error="Invalid
   email or password."` and `email=email`, on success sets
   `session["user_id"]`, `session.permanent = True`, redirects to
   `url_for("profile")`.
5. **`app.py`** — implemented `/logout` (`session.pop("user_id",
   None)` + redirect to `landing`) and moved it from the "Placeholder
   routes" banner section into the main "Routes" section, right after
   `login()`.
6. **`templates/login.html`** — form `action` changed from hardcoded
   `/login` to `{{ url_for('login') }}`.
7. **`templates/login.html`** — added `value="{{ email or '' }}"` to
   the email input so a failed login repopulates the email field
   (password field is never repopulated).
8. **`templates/base.html`** — wrapped `nav-links` in `{% if
   session.user_id %}` (shows "Sign out") / `{% else %}` (shows the
   previous "Sign in" + "Get started" links).

## Implementation checklist

All items complete — kept here (rather than deleted) so progress stays
auditable after the fact, matching the drift-guard convention used
while this was in progress:

- [x] 1. `database/db.py` — `get_user_by_email(email)` added
- [x] 2. `app.py` — `get_user_by_email` imported
- [x] 3. `app.py` — `check_password_hash` imported
- [x] 4. `app.py` — `/login` GET+POST implemented
- [x] 5. `app.py` — `/logout` implemented, moved out of placeholder banner
- [x] 6. `templates/login.html` — form action fixed to `url_for('login')`
- [x] 7. `templates/login.html` — email repopulated on failed login
- [x] 8. `templates/base.html` — nav wrapped in `{% if session.user_id %}`
- [x] 9. Manual end-to-end verification — all 5 flows pass (see below)
- [x] 10. Plan copied into `.claude/plans/03-login-and-logout.md`
- [x] 11. Spec/plan pairing convention documented in `.claude/commands/create-spec.md`
- [x] 12. CLAUDE.md route table updated (`/login`, `/logout`, and — on
      follow-up request — the stale `/register` "GET only" row too)

## Verification (Definition of Done, spec section 9)

Ran the dev server (`python app.py`) and drove it with `curl` +
a cookie jar to simulate the browser flow:

1. `GET /login` — form still renders, `action="/login"` now resolves
   via `url_for`. ✅
2. `POST /login` with `demo@spendly.com` / `demo123` — `302` to
   `/profile`; subsequent `GET /` shows `Sign out` in nav. ✅
3. `GET /logout` — `302` to `/`; subsequent `GET /` nav reverts to
   `Sign in`. ✅
4. `POST /login` with `demo@spendly.com` + wrong password —
   `"Invalid email or password."` shown, email field prefilled with
   `demo@spendly.com`. ✅
5. `POST /login` with `nobody@spendly.com` (no such user) — identical
   generic error message, confirming the two failure paths aren't
   distinguishable to the user. ✅
6. Cookie jar inspection confirmed the session cookie carries a
   persistent expiry (`session.permanent = True` took effect — Flask's
   default 31-day `PERMANENT_SESSION_LIFETIME`).

No database rows or files were created by this verification
(login/logout don't write to the DB); the background dev server used
for `curl` testing was stopped afterward.

## Explicitly out of scope

- `login_required` decorator / protecting any route
- Flash messages (errors stay on the existing `{% if error %}` pattern)
- CSRF protection
- "Remember me" checkbox (sessions are persistent by default instead)
- Distinguishing "no such email" from "wrong password" in the UI
- Rate limiting / account lockout, password reset
- Displaying the logged-in user's name in the nav
- Updating CLAUDE.md's "Implemented vs stub routes" table (asked
  separately, per CLAUDE.md's own rule)
