# Step 3 — Login and Logout

## 1. Problem Statement

Registration (Step 2) already creates users and signs them in on signup
(`session["user_id"] = user_id`), but there's no way back in afterward.
`/login` currently only renders the form (GET-only, no POST handler) and
`/logout` is a raw-string stub (`"Logout — coming in Step 3"`). A
registered user has no way to sign back in after their session ends, and
no way to deliberately sign out. This step wires up both: `/login` gains
a POST handler that verifies email/password against the `users` table
and establishes a session, and `/logout` clears that session. The nav
bar also becomes session-aware, since a "Sign out" link is the only way
a user would discover `/logout` exists.

## 2. Functional Requirements

- `GET /login` — renders `login.html` (unchanged from today).
- `POST /login` — accepts `email` and `password` form fields:
  - Look up the user by email.
  - If no user matches that email, **or** the password doesn't match
    the stored hash, re-render `login.html` with a single generic error:
    `"Invalid email or password."` (HTTP 200, same convention as
    `register()`'s error path). The form does not distinguish "email not
    found" from "wrong password" in the message shown to the user.
  - On success: set `session["user_id"] = user["id"]`, mark the session
    permanent (`session.permanent = True`) so it survives browser
    restarts, and redirect to `url_for("profile")` — same post-auth
    destination `register()` already uses (profile itself stays the
    Step 4 stub; landing there is expected and unchanged by this step).
- `GET /logout` — clears the session (`session.pop("user_id", None)`)
  and redirects to `url_for("landing")`. No confirmation step. Works
  whether or not a session currently exists (clearing a session that
  isn't there is a no-op, not an error).
- Nav bar (`base.html`) becomes session-aware: when `session.user_id` is
  set, show a "Sign out" link (→ `/logout`) instead of the current
  "Sign in" / "Get started" links. When no session, nav is unchanged
  from today.

## 3. APIs

**`POST /login`**
- Input: form-encoded body, fields `email` (string), `password` (string).
- Output:
  - Failure: `200 OK`, re-renders `login.html` with `error` (str) and
    `email` (str, repopulated — same as `register.html` repopulates
    `name`/`email` on failure) in the template context. Password is
    never repopulated.
  - Success: `302` redirect to `/profile` (via `url_for("profile")`),
    with `session["user_id"]` set and `session.permanent = True`.

**`GET /logout`**
- Input: none.
- Output: `302` redirect to `/` (`url_for("landing")`). Session cleared
  as a side effect.

**New internal function — `database/db.py`**
- `get_user_by_email(email)` → returns a `sqlite3.Row` (with `id`,
  `name`, `email`, `password_hash`, `created_at`) if a matching user
  exists, else `None`. Parameterized `SELECT`, follows the same
  `get_db()` / `try/finally: conn.close()` pattern as `create_user`.

## 4. Files and Interfaces Involved

- **`app.py`**
  - `import check_password_hash` addition is NOT needed here — password
    verification happens in `database/db.py` per the DB/password-logic
    boundary (see Constraints). `app.py` only needs the new
    `get_user_by_email` import alongside the existing `create_user`.
  - `/login` route: change `@app.route("/login")` to
    `@app.route("/login", methods=["GET", "POST"])`, add the POST branch
    (mirrors `register()`'s structure: `request.form.get(...)` →
    validate → error re-render vs. session-set + redirect).
  - `/logout` route: replace the stub body with the real implementation
    (clear session, redirect to `landing`). Move it out of the
    "Placeholder routes — students will implement these" banner section
    into the main `# Routes #` section, same as `register` was moved
    when Step 2 implemented it.
- **`database/db.py`**
  - Add `get_user_by_email(email)`.
  - Add `from werkzeug.security import check_password_hash` (alongside
    the existing `generate_password_hash` import) — password comparison
    happens inside a new small helper here (e.g. call
    `check_password_hash` at the point `app.py` needs a yes/no, wrapped
    so `app.py` never imports `werkzeug.security` itself). Simplest
    approach: `app.py` calls `get_user_by_email(email)` itself, then
    calls `check_password_hash(user["password_hash"], password)`
    directly — `check_password_hash` is a pure function with no DB
    access, so importing it in `app.py` doesn't violate the "only
    `db.py` touches `sqlite3`" rule. Decide at implementation time based
    on which reads cleaner; either is acceptable under CLAUDE.md.
- **`templates/login.html`**
  - Fix `action="/login"` → `action="{{ url_for('login') }}"` (matches
    the `url_for`-only convention already applied to `register.html`).
  - Add `value="{{ email or '' }}"` to the email input (repopulate on
    failed login, matching `register.html`'s pattern for `name`/`email`).
- **`templates/base.html`**
  - Wrap the `nav-links` block in `{% if session.user_id %}` /
    `{% else %}` — logged-in state shows a single "Sign out" link
    (`href="{{ url_for('logout') }}"`), logged-out state keeps today's
    "Sign in" + "Get started" links unchanged.
- **`templates/logout.html`** — not needed; `/logout` never renders a
  template, it only redirects.

## 5. Constraints

- Flask only, no blueprints, no app factory — route logic stays in
  `app.py`.
- No inline `sqlite3` in `app.py` — all queries go through
  `database/db.py`.
- Parameterized queries only (`?` placeholders) for `get_user_by_email`.
- Password verification uses Werkzeug's `check_password_hash` — no
  custom hashing, no new dependency.
- `PRAGMA foreign_keys = ON` already handled inside `get_db()` — nothing
  new needed here since login doesn't touch `expenses`.
- Error handling follows the established `register()` convention:
  plain `error` string passed to `render_template`, not `flask.flash`
  (flash is unused app-wide; this step doesn't introduce it).
- No CSRF protection (no Flask-WTF in the stack — consistent with
  registration's precedent).
- Session persistence: `session.permanent = True` on successful login,
  relying on Flask's default `PERMANENT_SESSION_LIFETIME` (31 days) —
  no new app.config needed unless a different duration is wanted later.
- Banner-comment style in `app.py` (`# --- Routes --- #` etc.) must be
  preserved; `/logout` moves out of the "Placeholder routes" section
  once implemented, same precedent as `/register`.
- `app.secret_key` is already set (`os.environ.get("SECRET_KEY") or
  os.urandom(24)`) — no changes needed there.

## 6. Out of Scope

- `/profile` staying a stub — this step does not implement Step 4. Login
  redirects there per existing precedent, but the page itself is
  unchanged.
- A `login_required` decorator / protecting any route from anonymous
  access — no route currently needs this (`/profile` and `/expenses/*`
  are still stubs), so it isn't built ahead of when it's needed.
- Displaying the logged-in user's name anywhere (nav, profile) — nav
  only gains a "Sign out" link, not a personalized greeting, since that
  would require a DB lookup on every page render for no current
  consumer.
- A "Remember me" checkbox in the UI — sessions are persistent by
  default for every login (per the interview answer), not conditionally
  based on a user-facing toggle.
- Distinguishing "no such email" from "wrong password" in the error
  message shown to the user (generic message only, per the interview
  answer) — this is a deliberate security choice, not an oversight.
- Rate limiting / account lockout after repeated failed logins.
- "Forgot password" / password reset flow.
- Updating the "Implemented vs stub routes" table in `CLAUDE.md` — per
  CLAUDE.md's own rule, that happens only after the user is asked,
  post-implementation.

## 7. Edge Cases and Error Handling

- **Email doesn't exist in `users`**: `get_user_by_email` returns
  `None` → generic `"Invalid email or password."` error, form
  re-rendered with email repopulated.
- **Email exists, password wrong**: `check_password_hash` returns
  `False` → same generic error as above (no distinction shown to user).
- **Empty email or password submitted**: form has `required` on both
  inputs (client-side), but a direct POST (e.g. via curl) with a blank
  field should still fail gracefully — `get_user_by_email("")` returns
  `None` → same generic error, not a 500.
- **`/logout` called with no active session**: `session.pop("user_id",
  None)` is a no-op if the key isn't present — still redirects to
  landing, no error.
- **Already-logged-in user visits `/login` (GET)**: out of scope for
  this step — renders the login form as normal, no redirect-if-already-
  authenticated behavior. (Not requested; would be scope creep.)
- **SQL injection via email/password fields**: prevented by
  parameterized queries in `get_user_by_email`, consistent with every
  other query in `database/db.py`.

## 8. Acceptance Criteria

- [ ] `GET /login` still renders `login.html` unchanged for a fresh visit.
- [ ] `POST /login` with the seeded demo credentials
      (`demo@spendly.com` / `demo123`) logs in successfully and redirects
      to `/profile`.
- [ ] `POST /login` with a wrong password shows `"Invalid email or
      password."`, re-renders `login.html`, and repopulates the email
      field (not the password field).
- [ ] `POST /login` with an email that has no matching user shows the
      same generic error message (not a different one).
- [ ] After a successful login, `session["user_id"]` is set and
      `session.permanent` is `True`.
- [ ] `GET /logout` while logged in clears the session and redirects to
      `/`.
- [ ] `GET /logout` while already logged out redirects to `/` without
      raising an error.
- [ ] Nav bar shows "Sign out" instead of "Sign in"/"Get started" when
      `session.user_id` is set, and reverts after logout.
- [ ] `login.html`'s form posts to `{{ url_for('login') }}`, not a
      hardcoded `/login` path.
- [ ] No inline `sqlite3` calls added to `app.py`; the new lookup lives
      in `database/db.py`.

## 9. End-to-End Verification

1. Run `python app.py`, visit `http://localhost:5001/login`.
2. Submit the seeded demo login (`demo@spendly.com` / `demo123`) →
   should redirect to `/profile` (the Step 4 stub string is expected —
   that's fine, it confirms the redirect happened) and the nav bar
   (visit `/` next) should now show "Sign out" instead of "Sign in".
3. Click "Sign out" (or visit `/logout` directly) → should land back on
   `/` with the nav bar showing "Sign in"/"Get started" again.
4. Visit `/login` again and submit a wrong password for
   `demo@spendly.com` → should see `"Invalid email or password."` on
   the page, with the email field still filled in and the password
   field blank.
5. Submit a nonexistent email (e.g. `nobody@spendly.com`) with any
   password → should see the same `"Invalid email or password."`
   message, confirming the two failure paths aren't distinguishable to
   the user.
