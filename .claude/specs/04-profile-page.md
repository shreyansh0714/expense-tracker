# Step 4 — Profile Page

## Problem Statement

Users currently have no way to view or update their account details after
registering — `GET /profile` is a placeholder stub that renders a static
"coming soon" page (`profile.html`). This feature turns `/profile` into a
real account page: view/edit name and email, set a personal monthly
budget, optionally change password, keep a personal notes field, and see
an at-a-glance read-only summary of the month's spending (total, category
breakdown, and a short recent-activity preview) — without duplicating the
full Expenses/Dashboard experience planned for later.

Building this also introduces two pieces of shared infrastructure the app
doesn't have yet: a login-required guard (no route in this codebase
currently protects itself — not even with a manual `session` check) and a
themed toast-notification component (the only existing transient UI is the
unrelated "How it works" video modal in `static/js/main.js`).

## Functional Requirements

**Auth guard (new, applies to both GET and POST):**
- If `session.get("user_id")` is missing, `flash()` a message
  ("Please sign in to view your profile.", category `"error"`) and
  `redirect(url_for("login"))`. No profile data is rendered or leaked.

**`GET /profile`** (logged in):
- Fetch the current user via a new `get_user_by_id(user_id)`.
- Render `profile.html` pre-filled with `name`, `email`, `monthly_budget`
  (blank input if `NULL`), and `notes` (blank if `NULL`).
- Also fetch and render the display content below.

**Display content (`GET /profile`, read-only — see Out of Scope for what
this deliberately does *not* include):**
- **Account summary**: a "Member since `<created_at>`" line, formatted for
  humans (e.g. "Member since Sep 2026") — no new query, `created_at`
  already comes back with the user row.
- **Monthly spend summary + category breakdown**: total ₹ spent in the
  current calendar month, plus a per-category breakdown (category, total)
  for the same window, sorted by total descending, via
  `get_monthly_category_totals(user_id)`. The total is the sum of the
  breakdown rows, not a second query. No expenses this month → total
  shows ₹0 and the breakdown list is empty, not an error.
- **Recent activity preview**: the user's **last 5 expenses** (date,
  category, amount), unpaginated, via `get_recent_expenses(user_id, 5)`.
  Fewer than 5 expenses on record → show however many exist; zero →
  an empty-state message, not an error.

**`POST /profile`** (logged in):
- Form fields: `name`, `email`, `monthly_budget` (optional), `notes`
  (optional, max 2000 characters), and an optional password-change group
  (`current_password`, `new_password`, `confirm_password`), plus
  `verification_code` (only meaningful/shown when `email` differs from the
  user's current email).
- Validation, in order, mirroring `register`'s if/elif style:
  1. `name` required (non-blank after `.strip()`).
  2. `email` must contain `"@"` (same weak check `register` uses — not
     strengthened here).
  3. `monthly_budget`, if non-blank, must parse as a number and be `>= 0`.
  4. `notes`, if non-blank, must be `<= 2000` characters after `.strip()`.
  5. If any of `current_password` / `new_password` / `confirm_password` is
     non-blank, all three are required; `current_password` must match the
     stored hash (`check_password_hash`); `new_password` must satisfy the
     same rule as registration (>=8 chars, at least one letter and one
     digit); `new_password == confirm_password`.
  6. If `email != user["email"]`: `verification_code` must equal the
     `PROFILE_EMAIL_BYPASS_CODE` environment variable (see Constraints) —
     this is a temporary stand-in for real OTP verification (see
     "Out of Scope" and the CLAUDE.md Future Tasks entry).
- Any validation failure re-renders `profile.html` with an `error` string
  and the submitted (non-password) field values echoed back — nothing is
  saved. The whole submission is atomic: a wrong verification code, for
  example, also discards a valid name/budget/notes change in the same
  request.
- On success: call `update_user(...)` (new function; also updates
  `password_hash` when a password change was submitted). Catch
  `sqlite3.IntegrityError` exactly like `register` does today, re-rendering
  with `"An account with this email already exists."` if the new email
  collides with a different account.
- On full success: `flash("Profile updated.", "success")`, then
  `redirect(url_for("profile"))` (Post/Redirect/Get).

**Toast component (new, shared, reused by both flows above):**
- Rendered once in `base.html` from `get_flashed_messages(with_categories=True)`
  (Jinja global — no import needed), styled from new CSS using existing
  tokens, shown/auto-dismissed by a small addition to `static/js/main.js`.
- Two categories: `"success"` (uses `--accent`) and `"error"` (uses
  `--danger`).

**Verification-code popup (new):**
- Shown client-side (JS) only when the `email` input's value differs from
  its original (page-load) value, right before form submit. Reuses the
  existing `.modal`/`.modal-overlay` CSS and open/close JS pattern already
  in the codebase rather than inventing new modal machinery.

**Nav:**
- Add a "Profile" link inside the existing
  `{% if session.user_id %}...{% endif %}` block in `base.html`, next to
  "Sign out", pointing to `url_for('profile')`.

## APIs

No JSON API — server-rendered forms only, consistent with `register`/`login`.

- `GET /profile` → 200 `profile.html` (logged in) or 302 → `/login` (not
  logged in).
- `POST /profile` → 302 → `/profile` on success; 200 `profile.html` with
  `error` set on validation failure; 302 → `/login` if session is missing.

Form fields consumed by `POST /profile`:

| Field | Required | Notes |
|---|---|---|
| `name` | yes | non-blank |
| `email` | yes | must contain `@` |
| `monthly_budget` | no | numeric string, `>= 0`, blank → `NULL` |
| `notes` | no | `<= 2000` characters, blank → `NULL` |
| `current_password` | only if changing password | |
| `new_password` | only if changing password | same rule as registration |
| `confirm_password` | only if changing password | must equal `new_password` |
| `verification_code` | only if `email` changed | must equal `PROFILE_EMAIL_BYPASS_CODE` |

## Files and Interfaces Involved

- **`app.py`**
  - Import `flash` from `flask` (alongside the existing imports).
  - Replace the `profile()` stub with the real GET/POST handler described
    above. Read the bypass code via
    `os.environ.get("PROFILE_EMAIL_BYPASS_CODE")` — never a literal in
    source.
- **`database/db.py`**
  - Add `monthly_budget REAL` and `notes TEXT` to the `users` table
    definition inside `init_db()`. Since a `database.db` created before
    this change already has the `users` table, also guard idempotent
    `ALTER TABLE users ADD COLUMN monthly_budget REAL` / `ADD COLUMN notes
    TEXT` calls (SQLite has no `ADD COLUMN IF NOT EXISTS`; wrap each in
    `try/except sqlite3.OperationalError` and ignore "duplicate column
    name") so existing dev databases pick up both columns without deleting
    seeded data.
  - Add `get_user_by_id(user_id)` — same connection/try-finally shape as
    `get_user_by_email`.
  - Add `update_user(user_id, name, email, monthly_budget, notes,
    password=None)` — same connection/try-finally shape as `create_user`;
    only rewrites `password_hash` when `password` is given; lets
    `sqlite3.IntegrityError` (duplicate email) propagate for `app.py` to
    catch, exactly like `create_user` does today.
  - Add `get_monthly_category_totals(user_id)` — `SELECT category,
    SUM(amount) as total FROM expenses WHERE user_id = ? AND date >= ? AND
    date < ? GROUP BY category ORDER BY total DESC`, with the current
    month's start/end computed in Python (same `date.today()` style
    `seed_db` already uses) and passed in as bind parameters. Read-only;
    same connection/try-finally shape as `get_user_by_email`.
  - Add `get_recent_expenses(user_id, limit=5)` — `SELECT * FROM expenses
    WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?`. Read-only;
    same connection/try-finally shape as `get_user_by_email`.
- **`templates/profile.html`** — replace the current `cta-section` "coming
  soon" stub with a real form using the `auth-card` / `form-group` /
  `form-input` / `btn-submit` conventions from `login.html`/`register.html`,
  plus the password-change fields, a `notes` textarea, and the
  verification-code popup markup (built on the existing `.modal`
  structure). Also renders the read-only display content: the member-since
  line, the monthly total + category breakdown, and the last-5 recent
  activity list — laid out as plain, functional markup for now (see Out of
  Scope: visual polish is the `spendly-ui-polish` skill's job, not this
  spec's).
- **`templates/base.html`** — add the "Profile" nav link; add the toast
  markup driven by `get_flashed_messages`.
- **`static/css/style.css`** — new `.toast` styles (success/error variants
  via `--accent`/`--danger`); no new modal CSS needed (reuses `.modal`).
- **`static/js/main.js`** — small addition: auto-show/dismiss toasts on
  load; show the verification popup when the email input's value changes
  from its original value, using the same open/close pattern as the
  existing "How it works" modal.

## Constraints

- Reuse the existing `.modal` CSS/JS pattern for the verification popup —
  do not build a second modal system.
- Reuse the existing password-validation rule from `register` (>=8 chars,
  1 letter, 1 digit) — do not invent a different rule.
- `PROFILE_EMAIL_BYPASS_CODE` is read from an environment variable via
  `os.environ.get(...)` and is **never** hardcoded in `app.py`, per
  CLAUDE.md's no-hardcoded-secrets rule. If the variable isn't set, treat
  every email-change attempt as unverifiable (see Edge Cases) — never fall
  back to a hardcoded default.
- All new DB access goes through `database/db.py`; parameterized queries
  only; connections opened with `get_db()` and closed in `finally`,
  matching `create_user`/`get_user_by_email`.
- No new pip dependencies — toast and popup are vanilla CSS/JS.
- Keep `app.py` route logic thin; mirror `register`'s if/elif validation
  style rather than introducing a different pattern.
- `notes` is capped at 2000 characters server-side — a reasonable bound
  against unbounded text, not something the user was asked to specify.
- `get_monthly_category_totals` and `get_recent_expenses` are read-only
  aggregate queries against `expenses` — this spec adds no way to create,
  edit, or delete an expense (that's Steps 7-9).

## Out of Scope

- **Real OTP email verification** for email changes — needs an actual
  email-sending mechanism and its own spec (tracked in CLAUDE.md's Future
  Tasks). `PROFILE_EMAIL_BYPASS_CODE` is an explicit, temporary,
  non-production stand-in only.
- **Budget threshold alerts** (e.g. a 90%-consumed toast) and any audit
  logging of those alerts — needs expense-aggregation logic that belongs
  with the future Dashboard feature, plus its own spec (tracked in
  CLAUDE.md's Future Tasks). This spec only adds the `monthly_budget`
  column and lets the user view/edit it — no alert logic.
- The Dashboard page itself (explicitly separate, planned later).
- **Full transaction history, pagination, or filtering of expenses** — the
  Profile page shows only a last-5 recent-activity preview; a real,
  paginated/filterable expense list belongs solely to the future Expenses/
  Dashboard page. Building that logic twice was considered and explicitly
  rejected during this spec's interview.
- **Multi-month or historical spend trends** — the spend summary and
  category breakdown are current-calendar-month only; comparisons across
  months are Dashboard territory.
- Visual polish beyond matching existing `style.css` tokens/patterns — the
  in-progress `spendly-ui-polish` skill
  (`.claude/skill-briefs/spendly-ui-polish.md`) handles beautification
  later; this spec only wires up correct, functional, on-brand markup.
- Account deletion, avatar/profile picture upload, or any field not listed
  in Functional Requirements.

## Edge Cases and Error Handling

- Not logged in, GET or POST → redirect to `/login` with an error toast; no
  profile data rendered or leaked.
- Blank `name` → error, nothing saved.
- Email missing `"@"` → error, nothing saved.
- `email` unchanged (exact string match to the loaded value) → verification
  code is not required at all, even if the field is present in the POST
  body.
- `email` changed to a value already used by a different account →
  duplicate-email error, regardless of whether the verification code was
  correct (the code only proves "you attempted verification"; it does not
  bypass the `UNIQUE` constraint).
- Verification code missing or wrong when `email` changed → error, and
  **nothing in the submission is saved** (not just the email — the request
  is atomic).
- `PROFILE_EMAIL_BYPASS_CODE` not set in the environment at all → every
  email-change attempt is treated as unverifiable; show the same "incorrect
  code" error until an admin sets the variable.
- `monthly_budget` left blank → stored as `NULL`. Non-numeric or negative
  input → validation error, nothing saved.
- Password-change fields partially filled (e.g. only `new_password` given)
  → error asking for all three fields.
- `current_password` wrong → error: "Current password is incorrect." (safe
  to be specific here since the user is already authenticated, unlike
  login's deliberately generic "Invalid email or password.")
- `new_password` fails the registration password rule, or
  `new_password != confirm_password` → error, nothing saved.
- A `database.db` created before this change (no `monthly_budget`/`notes`
  columns) → `init_db()`'s guarded `ALTER TABLE` calls add both columns on
  next app start without wiping existing users/expenses.
- `notes` longer than 2000 characters → validation error, nothing saved
  (including any other changed field in the same submission).
- No expenses logged this month → monthly total shows ₹0 and the category
  breakdown is an empty list, not an error.
- Fewer than 5 expenses on record (or zero) → the recent-activity preview
  shows however many exist, or an empty-state message at zero — never an
  error.

## Acceptance Criteria

- [ ] Visiting `/profile` while logged out redirects to `/login` and shows
      an error toast; no profile page content is ever rendered.
- [ ] Visiting `/profile` while logged in shows the current name, email,
      and monthly budget (blank if never set).
- [ ] Changing only `name` and saving updates it and redirects back to a
      profile page showing a "Profile updated." success toast.
- [ ] Changing `monthly_budget` to a valid non-negative number saves it;
      leaving it blank saves `NULL`; a negative or non-numeric value shows
      an error and saves nothing.
- [ ] Changing `email` to a new, unused address without the verification
      popup answered correctly does **not** save the change and shows an
      error.
- [ ] Changing `email` to a new, unused address, correctly entering the
      code from `PROFILE_EMAIL_BYPASS_CODE`, saves the new email.
- [ ] Changing `email` to an address already used by another account shows
      the duplicate-email error, even with a correct verification code.
- [ ] Submitting a password change with the correct current password and a
      valid, matching new/confirm password updates the password (next
      login with the new password succeeds; old password no longer works).
- [ ] Submitting a password change with the wrong current password shows
      "Current password is incorrect." and changes nothing.
- [ ] The nav shows a "Profile" link whenever a user is logged in.
- [ ] A fresh `database.db` (or one from before this change) ends up with
      `monthly_budget` and `notes` columns on `users` without losing
      existing rows.
- [ ] Profile shows a "Member since <date>" line matching the account's
      `created_at`.
- [ ] Profile shows the current month's total spend and a per-category
      breakdown that together match a manual `sqlite3` sum/group-by over
      the same account's expenses for the current month; with zero
      expenses this month, the total shows ₹0 and the breakdown is empty.
- [ ] Profile shows a "recent activity" list of the account's last 5
      expenses (date, category, amount), matching the 5 most recent rows
      by date in `sqlite3`; with fewer than 5 (or zero) expenses, it shows
      however many exist without erroring.
- [ ] Entering personal notes and saving persists them; reloading
      `/profile` shows the saved notes. Notes over 2000 characters show a
      validation error and save nothing.

## Manual Verification Guide

For all steps: run the app from the `expense-tracker/` folder with the venv
active: `source venv/bin/activate && python app.py`, then open
`http://localhost:5001` in your browser. Use the seeded demo account
(`demo@spendly.com` / `demo123`) unless a step says otherwise.

Before testing email-change verification, set the bypass code in the same
terminal you'll run the app from, **before** starting it:
```bash
export PROFILE_EMAIL_BYPASS_CODE=140605
python app.py
```

1. **Logged-out redirect + toast**
   - Open a private/incognito browser window (ensures no session cookie).
   - Go to `http://localhost:5001/profile`.
   - Expected: the browser lands on `/login`, and a toast/banner appears
     saying "Please sign in to view your profile."

2. **Profile shows current data**
   - Log in as `demo@spendly.com` / `demo123`.
   - Click "Profile" in the nav (or go to `/profile` directly).
   - Expected: the Name field shows "Demo User", Email shows
     "demo@spendly.com", and Monthly Budget is blank.

3. **Name change saves**
   - Change the Name field to "Demo User Two", click Save.
   - Expected: page reloads on `/profile`, shows "Profile updated." toast,
     and the Name field now shows "Demo User Two".

4. **Monthly budget validation**
   - Enter `-50` in Monthly Budget, click Save. Expected: an error message,
     nothing saved (reload `/profile` to confirm the old value is still
     there).
   - Enter `15000`, click Save. Expected: success toast, and reloading
     `/profile` shows `15000` in the field.

5. **Email change — wrong/no code**
   - Change Email to `demo2@spendly.com`. A popup should appear asking for
     a verification code. Leave it blank (or type `000000`) and confirm.
   - Expected: an error message, and the Email field still shows the
     original address after the page reloads/re-renders.

6. **Email change — correct code**
   - Repeat: change Email to `demo2@spendly.com`, and when the popup
     appears, type `140605` (matching the `PROFILE_EMAIL_BYPASS_CODE` you
     exported).
   - Expected: success toast, and `/profile` now shows
     `demo2@spendly.com`.

7. **Duplicate email**
   - Register a second account (any other email, e.g.
     `other@spendly.com`), then log back in as the first account
     (`demo2@spendly.com` after step 6) and try to change its email to
     `other@spendly.com`, entering the correct verification code.
   - Expected: "An account with this email already exists." error; the
     first account's email is unchanged.

8. **Password change**
   - On the Profile page, fill Current Password with the wrong value
     (e.g. `wrongpass1`), New Password `newpass123`, Confirm `newpass123`,
     save. Expected: "Current password is incorrect.", nothing changes.
   - Retry with the correct current password (`demo123`). Expected: success
     toast. Log out, then log back in using the new password (`newpass123`)
     — it should work. Trying the old password (`demo123`) should now fail.

9. **Database check for the new column**
   - Stop the app. In a terminal, from `expense-tracker/`, run:
     ```bash
     sqlite3 database.db "PRAGMA table_info(users);"
     ```
   - Expected output includes a row with `monthly_budget` as the column
     name (6 columns total: `id, name, email, password_hash, created_at,
     monthly_budget`).
   - Confirm no data was lost:
     ```bash
     sqlite3 database.db "SELECT id, name, email, monthly_budget FROM users;"
     ```
     Expected: your test accounts still listed, with the budget values you
     set above.

10. **Member-since line**
    - On `/profile`, find the "Member since" line.
    - Run: `sqlite3 database.db "SELECT created_at FROM users WHERE email='demo@spendly.com';"`
    - Expected: the date shown on the page matches (or is a
      human-readable version of) the `created_at` value from the command.

11. **Monthly spend summary + category breakdown**
    - Run this to compute the expected numbers yourself first:
      ```bash
      sqlite3 database.db "SELECT category, SUM(amount) FROM expenses WHERE user_id=(SELECT id FROM users WHERE email='demo@spendly.com') AND strftime('%Y-%m', date)=strftime('%Y-%m','now') GROUP BY category ORDER BY SUM(amount) DESC;"
      ```
    - Expected: the total shown on `/profile` equals the sum of that
      command's output, and the category list on the page matches the
      rows and order of that output (highest first). If the command
      returns nothing (e.g. the seed data was created in a different
      calendar month than today), `/profile` should show ₹0 and an empty
      breakdown, not an error.

12. **Recent activity preview**
    - Run: `sqlite3 database.db "SELECT date, category, amount FROM expenses WHERE user_id=(SELECT id FROM users WHERE email='demo@spendly.com') ORDER BY date DESC, id DESC LIMIT 5;"`
    - Expected: `/profile`'s "recent activity" list shows exactly these 5
      rows, in this order.

13. **Personal notes**
    - On `/profile`, type "Remember to review subscriptions" into the
      Notes field, save.
    - Expected: success toast, and reloading `/profile` still shows that
      text in the Notes field.
    - Paste in text longer than 2000 characters (e.g. run
      `python3 -c "print('a'*2001)"` and paste the output), save.
    - Expected: an error message, and the notes field still shows the
      *previous* saved value after reload (not the too-long text).

## End-to-End Verification

With the app running (`PROFILE_EMAIL_BYPASS_CODE` exported as above):
register a brand-new account → you land on `/profile` (already logged in
via the existing register flow), and immediately see a "Member since
today" line, a ₹0 monthly summary with an empty category breakdown, and an
empty recent-activity list (a new account has no expenses yet) → set a
monthly budget, write a personal note, and change your name → log out →
confirm `/profile` redirects to `/login` with a toast → log back in →
confirm the new name, budget, and note persisted → change your email with
the correct bypass code → log out and log back in using the **new** email
address and original password → change your password → log out and log
back in with the **new** password. Every step should succeed without
errors, and `sqlite3 database.db "SELECT * FROM users;"` should show
exactly one row for this account reflecting all the changes.
