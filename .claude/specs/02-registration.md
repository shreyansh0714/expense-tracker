# Step 2 — Registration

## 1. Problem Statement

`GET /register` currently renders `templates/register.html`, a complete sign-up
form (name, email, password) that posts to `/register` — but the route only
ever renders the page; it has no `POST` handler, so submitting the form does
nothing. The `users` table (`id`, `name`, `email UNIQUE`, `password_hash`,
`created_at`) already exists and is live via `database/db.py`'s `init_db()`,
and `werkzeug.security.generate_password_hash` is already imported and used
there to seed the demo user. This step wires the existing form to that
existing table: turn `/register` into a real account-creation endpoint that
validates input, hashes the password, inserts a row, logs the new user in via
a session, and sends them on to their account.

## 2. Functional Requirements

- `POST /register` accepts `name`, `email`, `password` form fields from
  `register.html`'s existing form.
- Server-side validation (in addition to the existing HTML5 `required`
  attributes):
  - `name`: non-empty after stripping whitespace.
  - `email`: non-empty, contains `@`, and not already present in `users`.
  - `password`: at least 8 characters, containing at least one letter and at
    least one digit.
- On any validation failure (empty field, malformed email, weak password,
  duplicate email), re-render `register.html` with an `error` message and
  HTTP 200 — same page, same form, previously entered `name`/`email`
  repopulated (not `password`, which is never round-tripped for security).
- On success:
  1. Hash the password with `generate_password_hash` (already imported in
     `database/db.py`).
  2. Insert a new row into `users` via a parameterized `INSERT`.
  3. Store the new user's id in the Flask session (`session["user_id"]`),
     logging them in immediately — no separate login step required.
  4. Redirect (`302`) to `/profile`.
- `/profile` remains the Step 4 stub (`"Profile page — coming in Step 4"`) —
  this step does not implement it. Redirecting a freshly-registered user
  there is expected to land on that stub string for now; that's normal until
  Step 4 lands, not a bug in this step.

## 3. APIs

**`POST /register`**

Request (`application/x-www-form-urlencoded`, from `register.html`'s form):

| Field | Type | Required |
|---|---|---|
| `name` | string | yes |
| `email` | string | yes |
| `password` | string | yes |

Responses:

| Outcome | Status | Response |
|---|---|---|
| Validation error / duplicate email | 200 | Re-rendered `register.html` with `error` (string) and the submitted `name`/`email` repopulated into the form |
| Success | 302 | Redirect to `/profile`; `session["user_id"]` set |

No JSON API — this is a classic server-rendered form post, consistent with
`/login`, `/register` (GET), and every other route in `app.py` today.

## 4. Files and Interfaces Involved

- **`app.py`**
  - Add `app.secret_key = ...` near the `Flask(__name__)` setup — required
    for `flask.session` to work. Source it from
    `os.environ.get("SECRET_KEY")`, falling back to `os.urandom(24)` for
    local dev, so no literal secret is hardcoded per project rules.
    Sessions won't persist across restarts in dev without a fixed env var —
    that's an accepted dev-only tradeoff, not a bug.
  - Change `@app.route("/register")` to
    `@app.route("/register", methods=["GET", "POST"])`.
  - `register()` branches on `request.method`: `GET` renders the form as
    today; `POST` runs validation, then either re-renders with `error` or
    inserts + sets session + redirects.
  - Import `request`, `redirect`, `url_for`, `session` from `flask` (only
    `Flask`, `render_template` are imported today).
- **`database/db.py`**
  - No schema changes — `users` table already has every column this needs.
  - New function `create_user(name, email, password)` (or equivalent) is the
    only place that runs the `INSERT INTO users` — routes never touch
    `sqlite3` directly, per the "DB logic → `database/db.py` only" rule.
    Must use a parameterized `INSERT ... VALUES (?, ?, ?)`, hash the
    password with `generate_password_hash` before insert, and let a
    duplicate-email `sqlite3.IntegrityError` (from the existing
    `email TEXT UNIQUE NOT NULL` constraint) surface so the route can catch
    it and turn it into the "email already registered" `error` message —
    no need for a separate pre-check `SELECT` when the `UNIQUE` constraint
    already guarantees it atomically.
- **`templates/register.html`**
  - Change `<form method="POST" action="/register">` to
    `<form method="POST" action="{{ url_for('register') }}">` — matches the
    `url_for`-only rule already followed by the `<a href="{{ url_for('login') }}">`
    link two lines below it.
  - Repopulate `value="{{ name or '' }}"` / `value="{{ email or '' }}"` on
    the `name`/`email` inputs so a validation error doesn't clear the form.
  - `{% if error %}` block already exists — no template structural change
    needed there.
- **`templates/login.html`**
  - Out of scope for this step (see below) — left untouched.

## 5. Constraints

- Flask + Werkzeug + stdlib `sqlite3` only — no new dependencies (no
  Flask-WTF, no email-validator package). Email format check is a plain
  `"@" in email` substring check, not a regex library.
- No ORM — raw parameterized SQL only, through `database/db.py`.
- No blueprints, no app factory — route stays in `app.py`.
- Passwords: never stored or logged in plaintext; always through
  `generate_password_hash` / eventual `check_password_hash`.
- `PRAGMA foreign_keys = ON` is already set in `get_db()` — no change
  needed there.
- Keep the existing banner-comment style in `app.py`
  (`# ---...--- #` / title / `# ---...--- #`) if a new section boundary is
  needed; otherwise `register()` just moves within the existing "Routes"
  section since it's no longer a placeholder.
- Once implemented, `/register` must render a template on every path (GET,
  validation failure, success-redirect) — never fall back to a raw string
  response, per the "implemented stub routes render a template" rule.

## 6. Out of Scope

- `/login`'s `POST` handler — stays GET-only/unimplemented this step (per
  the roadmap, `/login` POST and `check_password_hash` land later).
- `/logout` — still the Step 3 stub string.
- Flash messages / `base.html` flash rendering — errors use the existing
  `register.html` `{% if error %}` block, not `flask.flash`.
- Nav bar becoming session-aware (showing the logged-in user's name instead
  of "Sign in" / "Get started") — `base.html` nav is untouched.
- `/profile` implementation — still returns its Step 4 stub string; this
  step only redirects to it.
- Rate limiting, CAPTCHA, or email verification/confirmation flow.
- CSRF protection (no Flask-WTF in the stack; not introduced here).
- "Remember me" / session expiry configuration.

## 7. Edge Cases and Error Handling

| Case | Handling |
|---|---|
| Empty `name` (whitespace only) | 200, re-render with `error="Name is required."` |
| Malformed/empty `email` | 200, re-render with `error="Please enter a valid email address."` |
| Email already registered | 200, re-render with `error="An account with this email already exists."`; caught via `sqlite3.IntegrityError` from the `UNIQUE` constraint, not a duplicate app-level query |
| Password under 8 chars, or missing a letter/digit | 200, re-render with `error="Password must be at least 8 characters and include a letter and a number."` |
| Missing form field entirely (e.g. request forged without `password`) | Treated as empty string via `request.form.get(field, "")`, falls into the same validation error path — no 400/`KeyError` |
| Successful registration | 302 to `/profile`, `session["user_id"]` set |
| DB file/table missing | Not handled specially — `init_db()` already runs at app startup, so this shouldn't occur in normal operation |

## 8. Acceptance Criteria

- [ ] `GET /register` still renders the form exactly as today (no regression).
- [ ] `POST /register` with valid name/email/strong-password creates a new
      row in `users` with a hashed (not plaintext) password.
- [ ] Successful registration sets `session["user_id"]` and redirects to
      `/profile`.
- [ ] Submitting a duplicate email re-renders `register.html` with an error
      and does not create a second row.
- [ ] Submitting a short/weak password re-renders with an error and creates
      no row.
- [ ] Submitting an empty name or malformed email re-renders with an error
      and creates no row.
- [ ] `register.html`'s form `action` uses `url_for('register')`, not a
      hardcoded path.
- [ ] No raw `sqlite3` calls appear in `app.py` — all DB access goes through
      `database/db.py`.
- [ ] `app.secret_key` is set from an environment variable with a dev-only
      fallback, never a literal hardcoded string.

## 9. End-to-End Verification

With the venv active and `python app.py` running on port 5001:

1. Visit `http://localhost:5001/register`, submit a new name/email (not
   `demo@spendly.com`) and a password like `Passw0rd`.
2. Confirm the browser is redirected to `/profile` and shows the Step-4 stub
   string (expected — not a failure).
3. Re-submit the same form with the same email again — confirm it
   re-renders `register.html` with a duplicate-email error and the page
   still shows the previously entered name/email in the fields.
4. Inspect `database.db` (`sqlite3 database.db "SELECT id, name, email FROM users;"`)
   and confirm exactly one new row was added for step 1, not two.
5. Submit a password like `abc` (too short) — confirm it re-renders with the
   password-strength error and no new row is added.
