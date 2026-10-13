# Spec 10 — Security & reliability basics

**Status:** Draft — not yet implemented
**Branch:** `feature/security-and-reliability` (branched off `main` at
`0226a26`, after PR #17)
**Date:** 2026-10-02

**Why this is one grouped spec:** a six-reviewer portfolio review
(recruiter, senior engineer, talent acquisition, HR, non-tech user,
mentor) found a set of basic safety and reliability gaps. The developer
asked for similar tasks to be grouped into a few specs rather than one
spec per task. Everything here is about "can this app be trusted": forms
can't be forged, the live demo can't be broken by a visitor, the test
suite passes on any day and in any timezone, and it runs automatically on
GitHub. The full roadmap is in the local plan
`.claude/plans/10-11-readme-roadmap.md`.

**Design reference:** none. The only new visible pieces are the demo
banner and the "Sign out" button, which reuse existing styles (`.toast`,
nav link styling). No mockup exists, so no mockup text applies (see
CLAUDE.md, "Mockup content convention").

---

## 1. Problem Statement

Spendly is live at https://spendly-web-production-03e3.up.railway.app,
and reviewers found these gaps:

| # | Gap today | Why it matters |
|---|---|---|
| G1 | No form has CSRF protection, and logout is a plain link (`GET /logout`, `app.py:299`) | Another website could make a logged-in user's browser delete expenses, change their budget, or change their password without them knowing |
| G2 | The shared demo account (`demo@spendly.com`) can be edited by anyone | One visitor can change its password and lock every later visitor, including recruiters, out of the demo |
| G3 | `app.secret_key` silently falls back to a random key (`app.py:31`); no session-cookie settings exist; login and register don't reset the session; register doesn't set `session.permanent` (`app.py:276`) | A missing variable on Railway would log everyone out on every restart; cookies are missing the standard safety flags |
| G4 | The test suite fails on `main`: 90 tests, 84 pass, 6 fail. One failure is the `created_at` UTC/IST date bug; five are Step 9 tests whose data is dated September, so they broke when the month changed | A "tested" project with a failing suite isn't credible, and the project's own workflow forbids committing with failing tests |
| G5 | Tests touch the real `database.db`: `tests/conftest.py:3` imports `app` before the database path is swapped, and `app.py:33-35` runs `init_db()` and `seed_db()` against `database.db` on import | Breaks the rule "tests never touch database.db" |
| G6 | "Today" comes from the server clock (`date.today()`). Railway and GitHub run in UTC while users are in India (IST, UTC+5:30). `local_time()` (`app.py:63-65`) also converts to the server's zone | Between 00:00 and 05:30 IST, the date filter, "Showing" line and "edited at" times are a day or 5.5 hours off on the live site |
| G7 | Nothing runs the tests automatically | Regressions only show up if someone remembers to run pytest |
| G8 | Small leftovers: no index on `expenses(user_id, date)`; a stale `# Placeholder routes — students will implement these` comment (`app.py:325`) sits above real routes; spec 03 still describes `GET /logout` and `session.pop` | Slow queries later; misleading code; and the test-writer, which reads specs only, would write wrong logout tests |

## 2. Functional Requirements

### FR1 — CSRF protection on every POST form
- FR1.1: Each session gets one random token, stored in `session["csrf_token"]`, created the first time a page needs it (`secrets.token_hex(32)`).
- FR1.2: Templates get a `csrf_token()` function (registered with a context processor) and every POST form includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`. The 8 POST forms are:
  - `templates/login.html:20`
  - `templates/register.html:20`
  - `templates/add_expense.html:43` (edit) and `:46` (add)
  - `templates/profile.html:71` (budget), `:289` (profile edit), `:339` (delete popup)
  - the new logout form in `templates/base.html` (FR2)
  The GET filter forms at `profile.html:50` and `:56` get **no** token.
- FR1.3: One `@app.before_request` check runs on every POST. If `request.form["csrf_token"]` is missing or doesn't match `session["csrf_token"]` (compared with `hmac.compare_digest`), the request is refused before the route runs: nothing is saved, the user gets a red toast **"Your form expired. Please try again."** (`flash(..., "error")`) and is redirected (302) back to the page they came from. `request.referrer` is used **only if its host equals `request.host`**; otherwise (missing, or another site, which is exactly what a forged request looks like) the redirect goes to `url_for("landing")`, i.e. `/`. This stops the check itself from becoming an open redirect to an attacker's site.
- FR1.4: There are no exempt routes. Login and register are protected too, which blocks "login CSRF".
- FR1.5: No new package. This is hand-written with stdlib `secrets` and `hmac`, roughly 15 lines.

### FR2 — Logout becomes a POST button
- FR2.1: `/logout` accepts only POST. A GET to `/logout` returns **405 Method Not Allowed**.
- FR2.2: The nav "Sign out" link in `base.html:32` becomes a small `<form method="post" action="{{ url_for('logout') }}">` with the CSRF hidden input and a `<button>` styled to look like the other nav links. The visible text stays "Sign out".
- FR2.3: Logout runs `session.clear()` (replacing `session.pop("user_id")` at `app.py:301`) and redirects to the landing page as before.

### FR3 — Demo account: profile settings locked
- FR3.1: A constant `DEMO_EMAIL = "demo@spendly.com"` identifies the demo user. The check compares the logged-in user's email from the database (`get_user_by_id(session["user_id"])["email"]`).
- FR3.2: **Locked:** `POST /profile` (name, email, notes, password). For the demo user nothing is saved, and the user is redirected (302) to `/profile` with the red toast **"The demo account's profile can't be changed. Create your own free account to try this."**
- FR3.3: **Allowed** for the demo user, unchanged: `POST /profile/budget`, `POST /expenses/add`, `POST /expenses/<id>/edit`, `POST /expenses/<id>/delete`.
- FR3.4: **Banner:** when the demo user views `GET /profile`, a one-line note shows at the top of the page: **"You're using the shared demo account. Profile settings are locked — create your own free account to try them."** "create your own free account" links to `url_for('register')`. Other users never see it.
- FR3.5: The Edit profile button stays visible for the demo user; the server-side lock is the real protection.
- FR3.6: The demo password `demo123` (7 characters) breaks the app's own "at least 8 characters, a letter and a number" rule (`app.py:255`). This is a **deliberate exemption**: the demo's password can't be changed, and visitors need a short password to type. It is documented here and in the README.
- FR3.7: Resetting drifted demo data stays **manual** (re-seeding after a deploy, with the developer's explicit yes). There's no automatic reset.

### FR4 — Secret key and session-cookie basics
- FR4.1: When the `RAILWAY_ENVIRONMENT` variable is set (production), a missing `SECRET_KEY` stops the app at startup with `RuntimeError("SECRET_KEY must be set in production")`. Locally (no `RAILWAY_ENVIRONMENT`), the random `os.urandom(24)` fallback stays.
- FR4.2: Set `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = "Lax"`, and `SESSION_COOKIE_SECURE = True` only when `RAILWAY_ENVIRONMENT` is set, because local dev runs on plain `http://`.
- FR4.3: Login and register both run `session.clear()` before setting `session["user_id"]`, so a pre-login session can't be reused. Both set `session.permanent = True` (register doesn't today). The session lifetime stays Flask's default of 31 days.

### FR5 — One "today", in IST
- FR5.1: `database/db.py` defines `IST = timezone(timedelta(hours=5, minutes=30))` and `today_ist()`, which returns `datetime.now(IST).date()`. These are stdlib only, with no `zoneinfo` or `tzdata` package. IST has no daylight saving, so a fixed offset is exact.
- FR5.2: `app.py` imports `today_ist` and uses it everywhere it used `date.today()`: `app.py:342`, `:385`, `:504`, `:553`. `seed_db()` uses it for the demo seed dates (`db.py:94`).
- FR5.3: **Signup-date bug (`app.py:335-336`):** `users.created_at` is stored in UTC by SQLite's `datetime('now')`. Parse it as UTC and convert it to `IST` before taking `.date()`. Example: an account created at `2026-10-01 20:00:00` UTC was created on **2 Oct 2026** in IST, so its "Showing" line starts at 2 Oct.
- FR5.4: `local_time()` (`app.py:63-65`) converts to `IST` instead of the server's local zone, so "edited at" times are correct on Railway.

### FR6 — Tests isolated from `database.db`
- FR6.1: `DB_PATH = os.environ.get("SPENDLY_DB", "database.db")` in `database/db.py`. The default keeps the Railway start command (`ln -sf /data/database.db database.db`) working unchanged.
- FR6.2: `tests/conftest.py` sets `os.environ["SPENDLY_DB"]` to a temporary file path **before** `from app import app`, so the import-time `init_db()` and `seed_db()` never open `database.db`. The per-test `monkeypatch` of `db.DB_PATH` to `tmp_path/"test.db"` stays.
- FR6.3: `conftest.py` asserts `db.DB_PATH != "database.db"` so a regression fails loudly.
- FR6.4: CLAUDE.md's test-isolation sentence (`CLAUDE.md`, "Spec-Driven Development (SDD) workflow" section) is reworded to: "conftest sets `SPENDLY_DB` to a temp file before importing `app`, then monkeypatches `DB_PATH` per test."

### FR7 — Shared CSRF helper for tests
- FR7.1: `tests/conftest.py` provides `csrf_post(client, url, data=None, **kwargs)`. Right before each post it writes a fresh token into the session (`with client.session_transaction() as s: s["csrf_token"] = token`) and adds `csrf_token=token` to the form data. It has to run per post, not once per fixture, because login now clears the session (FR4.3).
- FR7.2: The `auth_client` fixture's register and login posts use `csrf_post`. All 39 existing `.post(` calls in `tests/` switch to `csrf_post`, except tests that deliberately check CSRF rejection.
- FR7.3: `tests/test_09-delete-button-feature.py:243` (`client.get("/logout")`) becomes `csrf_post(client, "/logout")`.
- FR7.4: `.claude/agents/spendly-test-writer.md` (around line 30) gains the rule: "For every `.post`, use the `csrf_post` helper from `tests/conftest.py`." CLAUDE.md's `tests/conftest.py` line in the Architecture tree mentions `csrf_post`.

### FR8 — Green, date-proof test suite
- FR8.1: All 6 currently failing tests pass.
- FR8.2: Tests stop depending on the calendar. Fixture dates are computed relative to `today_ist()` (imported from `database.db`, the public helper this spec defines) instead of hard-coded dates like `2026-09-22` or `date.today()`. The tests then pass in any month and any timezone.
- FR8.3: **Test hooks for the signup-date bug (approved exception):** the test that proves FR5.3 may (a) patch `app.today_ist` with monkeypatch (not `db.today_ist`, because `app` imports the name directly), and (b) set the user's `created_at` with a direct `UPDATE users SET created_at = ?` through `db.get_db()` on the temp database. This is an approved exception to the test-writer's "set up data only through routes" rule. It's recorded here and in `spendly-test-writer.md`.
- FR8.4: **Demo user in tests (approved exception):** the test database is created by `db.init_db()` only, so it has no demo user, and `demo123` can't be registered through `/register` (it fails the password rule). Tests for FR3 may call `db.seed_db()` on the temp database to create `demo@spendly.com` / `demo123`.
- FR8.5: **Startup settings in tests:** FR4.1 and FR4.2 run when `app` is imported. Tests check them with `monkeypatch.setenv(...)` (and `monkeypatch.delenv("SECRET_KEY", raising=False)`) followed by `importlib.reload(app)`, with `SPENDLY_DB` still pointing at the temp path. After the test, reload `app` once more with the normal environment so later tests aren't affected.

### FR9 — CI on GitHub Actions
- FR9.1: New `.github/workflows/tests.yml` runs on every push and pull request. It runs on `ubuntu-latest` with Python `3.13` (matching the local venv), runs `pip install -r requirements.txt`, then `python -m pytest -q`.
- FR9.2: The job sets `env: TZ: Asia/Kolkata` as a backup, so any remaining `date.today()` matches IST.
- FR9.3: The job needs no secrets. `RAILWAY_ENVIRONMENT` isn't set there, so FR4.1 doesn't apply.
- FR9.4: The README status badge for this workflow is added later in the README rework (Part 3 of the plan), not in this spec.

### FR10 — Small leftovers
- FR10.1: `init_db()` runs `CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date)`.
- FR10.2: Delete the stale comment banner `# Placeholder routes — students will implement these` (`app.py:325`), keeping the surrounding banner style for the real section name.
- FR10.3: Spec 03 (`.claude/specs/03-login-and-logout.md`, lines around 31, 52, 188-190, 206) is updated wherever it describes `GET /logout` or `session.pop`, to say POST + `session.clear()` + CSRF token, each marked "(superseded by Spec 10)". This must happen **before** `/test-feature 03-login-and-logout` is ever run.
- FR10.4: `.claude/PROGRESS.md:37` route row becomes `POST /logout`.

## 3. APIs

| Route | Method | Input | Output (success) | Output (refusal) |
|---|---|---|---|---|
| any POST route | POST | form field `csrf_token` (64 hex chars) plus the route's usual fields | the route's usual behaviour | missing/wrong token → 302 to the same-site `Referer`, else `/`; toast "Your form expired. Please try again."; nothing saved |
| `/logout` | POST | `csrf_token` | session cleared, 302 to `/` | — |
| `/logout` | GET | — | — | 405 Method Not Allowed |
| `/profile` | POST (demo user) | the usual profile fields | — | 302 to `/profile`, toast "The demo account's profile can't be changed. Create your own free account to try this.", nothing saved |
| `/profile` | GET (demo user) | — | page includes the demo banner (FR3.4) | — |

Session data: `session["csrf_token"]` (string), `session["user_id"]` (int), `session.permanent = True` after login or register.

## 4. Files and Interfaces Involved

| File | Change |
|---|---|
| `app.py` | CSRF context processor + `before_request` check; `logout` POST-only + `session.clear()`; `DEMO_EMAIL` + demo lock in `profile()` POST + `is_demo` passed to the template; `RAILWAY_ENVIRONMENT`/`SECRET_KEY` check + cookie config; `session.clear()` + `session.permanent` in login/register; `today_ist` at 4 call sites; `created_at` UTC→IST; `local_time` → IST; delete stale banner |
| `database/db.py` | `DB_PATH` from `SPENDLY_DB`; `IST` + `today_ist()`; seed dates use `today_ist()`; index in `init_db()` |
| `templates/base.html` | logout form button; CSRF input |
| `templates/login.html`, `register.html`, `add_expense.html`, `profile.html` | CSRF hidden inputs; demo banner in `profile.html` |
| `static/css/style.css` | nav-button reset so "Sign out" looks like a link; demo banner style (existing tokens only) |
| `tests/conftest.py` | `SPENDLY_DB` before import; `assert db.DB_PATH != "database.db"`; `csrf_post` helper; fixtures use it |
| `tests/test_06-date-time-filter.py`, `tests/test_06b-profile-dashboard-restructure.py`, `tests/test_09-delete-button-feature.py` | posts via `csrf_post`; dates relative to `today_ist()`; logout via POST |
| `.github/workflows/tests.yml` | new CI workflow |
| `.claude/agents/spendly-test-writer.md` | `csrf_post` rule + FR8.3 exception |
| `CLAUDE.md` | test-isolation sentence (FR6.4); `conftest.py` line mentions `csrf_post` |
| `.claude/specs/03-login-and-logout.md` | superseded logout lines (FR10.3) |
| `.claude/PROGRESS.md` | `POST /logout` row; Known issues gains: money stored as float (incl. the float `==` at `app.py:587`); per-user timezones (app assumes IST); Flask dev server in production (gunicorn would be a new package); no login rate limiting; try/except `ALTER` migrations and an `UPDATE` on every boot; one large `app.py` (135-line `profile()`, duplicated validation, `filter_args` ×3, copy-pasted sign-in check); email change uses a bypass code, not real OTP; `/analytics` placeholder; no test files for Steps 1, 4, 5; hand-drawn card borders kept by design; demo password exempt from the password rule (FR3.6) |

## 5. Constraints

- No new pip packages (CLAUDE.md "Preferred libraries"). CSRF uses stdlib `secrets` and `hmac`; IST uses stdlib `datetime.timezone`.
- Routes stay in `app.py`; DB code stays in `database/db.py`; templates extend `base.html`; CSS uses existing `:root` tokens only.
- `app.run(debug=True, port=5001)` is unchanged.
- Production start command and Railway volume are unchanged (the `SPENDLY_DB` default is `database.db`).
- `SECRET_KEY` is already set on Railway (PROGRESS.md, "Live deployment"); confirm before redeploying.
- Commits and PRs carry no Claude attribution and need the developer's explicit yes.

## 6. Out of Scope

- A shared `@login_required` decorator (the copy-pasted sign-in check stays; listed under Known issues).
- Login rate limiting, gunicorn, storing money as integer paise, per-user timezones, real email OTP (all Known issues).
- Automatic demo-data reset; re-seeding stays manual.
- Changing the session lifetime (stays 31 days).
- Any README change, including the CI badge (README rework, Part 3).
- Profile display fixes (dates on one line, "Latest 5 of 8", sticky note, landing tweaks): that's Spec 11.
- New tests for Steps 2, 3, 7 and 8 beyond updating existing ones (separate `/test-feature` runs after this spec).

## 7. Edge Cases and Error Handling

| Case | Handling |
|---|---|
| A form page was open across a logout/login (session cleared, token changed) | Token mismatch → "Your form expired. Please try again." and back to the page; the user resubmits |
| No `Referer` header (some privacy settings) | Redirect to `/` with the same toast |
| Forged POST whose `Referer` is another site (e.g. `https://evil.example/`) | Redirect to `/`, never to the other site (FR1.3) |
| POST with no session at all (cookie blocked) | No `session["csrf_token"]` → refused the same way |
| Demo user submits the profile form with a valid CSRF token | Lock applies after the CSRF check: nothing saved, demo toast, back to `/profile` |
| Demo user deletes every expense | Allowed by design (FR3.3); dashboard shows its existing empty states; data is re-seeded manually later |
| Someone registers a new account with email `demo@spendly.com` | Already impossible: the email is taken (existing "An account with this email already exists." error) |
| `SECRET_KEY` missing on Railway | App refuses to start with a clear error instead of silently logging everyone out |
| Signup at 20:00 UTC on 1 Oct | Counted as 2 Oct (IST), matching the user's calendar |
| Tests run at 19:00 UTC (00:30 IST next day) | Tests use `today_ist()`, so they agree with the app; CI also sets `TZ=Asia/Kolkata` |
| `SPENDLY_DB` unset | Defaults to `database.db`, so local dev and Railway behave exactly as today |

## 8. Acceptance Criteria

- [ ] AC1: Every POST form listed in FR1.2 renders a hidden input named `csrf_token` whose value is 64 hex characters, and the value equals `session["csrf_token"]`. On `/profile` there are 4 such inputs (Sign out, budget, profile edit, delete popup) **only when the user has at least one expense**: the delete popup is rendered only then. A user with no expenses has 3.
- [ ] AC2: A POST to `/expenses/add` (logged in) **without** `csrf_token` saves nothing (expense count unchanged) and returns 302 with `Location` `/` (the test client sends no `Referer`). Following the redirect shows the toast "Your form expired. Please try again.". With a same-site `Referer` of `http://localhost/expenses/add`, the `Location` is that page instead.
- [ ] AC3: The same POST with a **wrong** `csrf_token` behaves exactly as AC2.
- [ ] AC3b: The same POST with no token and `Referer: https://evil.example/page` redirects to `/`, never to `evil.example`.
- [ ] AC4: A POST to `/login` with correct credentials but no `csrf_token` does not log in (`session` has no `user_id`).
- [ ] AC5: With a valid token, every existing form still works as before (add, edit, delete, budget, profile, login, register).
- [ ] AC6: `GET /logout` returns 405.
- [ ] AC7: `POST /logout` with a valid token returns 302 to `/`, and afterwards the session contains neither `user_id` nor anything else set before logout.
- [ ] AC8: The nav shows a "Sign out" control that is a `<button>` inside a `<form method="post">` pointing at `/logout`.
- [ ] AC9: Logged in as `demo@spendly.com`, a valid `POST /profile` changing the name returns 302 to `/profile`, the toast reads "The demo account's profile can't be changed. Create your own free account to try this.", and the stored name is still "Demo User". (In the page source, Jinja escapes the apostrophes as `&#39;`, so compare against the HTML-unescaped page text.)
- [ ] AC10: Same as AC9 for an email change and for a password change (password still `demo123`).
- [ ] AC11: Logged in as the demo user, `POST /profile/budget`, `POST /expenses/add`, `POST /expenses/<id>/edit` and `POST /expenses/<id>/delete` all work normally.
- [ ] AC12: `GET /profile` as the demo user shows "You're using the shared demo account. Profile settings are locked — create your own free account to try them." with a link to `/register`; as any other user the text is absent.
- [ ] AC13: A non-demo user can still change their own name, email (with the bypass code) and password. The profile form always submits `name` and `email` together (plus `notes`, and the password fields only when changing the password), so a name change posts the new `name` with the user's current `email`; success shows the toast "Profile updated.".
- [ ] AC14: With `RAILWAY_ENVIRONMENT` set and `SECRET_KEY` unset, importing `app` raises `RuntimeError` with "SECRET_KEY must be set in production".
- [ ] AC15: `app.config["SESSION_COOKIE_HTTPONLY"]` is `True` and `app.config["SESSION_COOKIE_SAMESITE"]` is `"Lax"`; `SESSION_COOKIE_SECURE` is `True` only when `RAILWAY_ENVIRONMENT` is set.
- [ ] AC16: After register, the session cookie is permanent (`session.permanent` is `True`), same as after login.
- [ ] AC17: A session value set before login (e.g. `session["x"] = 1` via `session_transaction`) is gone after a successful login.
- [ ] AC18: A user whose `created_at` is `2026-10-01 20:00:00` (UTC), viewed with `today_ist()` patched to 2 Oct 2026, sees "Showing 2 Oct 2026 – 2 Oct 2026" on a fresh account.
- [ ] AC19: `local_time("2026-10-01 20:00:00")` returns exactly `2 Oct 2026, 1:30 AM` (IST), regardless of the machine's own timezone.
- [ ] AC19b: With `app.today_ist` patched to return 3 Oct 2026 (the IST date of the instant 2 Oct 2026 19:00 UTC), `GET /profile` on the default "This month" range shows a "Showing" line ending on `3 Oct 2026`.
- [ ] AC20: `venv/bin/python -m pytest` reports 0 failures.
- [ ] AC21: In a clean checkout with no `database.db`, running pytest leaves no `database.db` behind; `conftest.py` asserts `db.DB_PATH != "database.db"`.
- [ ] AC22: `.github/workflows/tests.yml` exists, runs on push and pull_request, and its run on the PR for this branch is green.
- [ ] AC23: `sqlite3 database.db ".indexes expenses"` lists `idx_expenses_user_date` after the app starts once.
- [ ] AC24: `app.py` no longer contains "students will implement these".
- [ ] AC25: Spec 03 no longer describes `GET /logout` or `session.pop` as current behaviour (each such line is marked superseded by Spec 10); `spendly-test-writer.md` mentions `csrf_post`; `PROGRESS.md` lists `POST /logout`.

## 9. Manual Verification Guide

Start the app first: in Terminal, `cd` into the project folder, run
`source venv/bin/activate`, then `python app.py`, and open
**http://127.0.0.1:5001** in Chrome. Keep that terminal open. For
commands below, open a **second** Terminal tab in the same folder.

**AC1 — hidden token on every form**
1. Go to http://127.0.0.1:5001/login.
2. Right-click the page → **View Page Source**. Press Cmd+F and search `csrf_token`.
3. Expected: one line like `<input type="hidden" name="csrf_token" value="3f9a…">`, where the value is a long string of 0–9 and a–f (64 characters).
4. Repeat on /register, /expenses/add, /profile (expect 4 hits on /profile: budget form, profile form, delete popup, Sign out), and an edit page (click the pencil on any expense).

**AC2 / AC3 — a forged add is refused**
1. Log in. Open DevTools (Cmd+Option+I) → **Elements** tab.
2. Go to /expenses/add. In Elements, press Cmd+F, search `csrf_token`, double-click the `value="…"` text and delete it (AC2) or change one character (AC3). Press Enter.
3. Fill in the form normally and click Save.
4. Expected: you land back on the add page with a red toast "Your form expired. Please try again.", and /profile shows no new expense.

**AC3b — never redirected to another site**
Run (logged out is fine): `curl -i -X POST -H "Referer: https://evil.example/page" http://127.0.0.1:5001/login`
Expected: `302 FOUND` and a `Location: /` line, not `evil.example`.

**AC4 — login needs the token**
1. Log out. Go to /login, open DevTools → Elements, delete the `csrf_token` input's value as above.
2. Log in with correct details.
3. Expected: you stay on the login page with the red "Your form expired. Please try again." toast and are not signed in (nav still shows "Sign in").

**AC5 — normal use still works**
Without touching DevTools: add an expense, edit it, delete it, set a budget, change your profile name, log out, log back in, register a new account. Expected: every action succeeds exactly as before.

**AC6 — GET logout refused**
In the second terminal run: `curl -i http://127.0.0.1:5001/logout`
Expected: the first line contains `405 METHOD NOT ALLOWED`.

**AC7 / AC8 — the Sign out button**
1. Logged in, open DevTools → Elements, find "Sign out" in the nav.
2. Expected: it sits inside `<form method="post" action="/logout">` and is a `<button>`.
3. Click it. Expected: you land on the landing page, logged out. DevTools → **Application** → Storage → Cookies → `http://127.0.0.1:5001`: the `session` cookie is gone or no longer holds your login.

**AC9 / AC10 — demo profile is locked**
1. Log in as `demo@spendly.com` / `demo123`.
2. On /profile click Edit profile, change the name to "Hacker", click Save.
3. Expected: red toast "The demo account's profile can't be changed. Create your own free account to try this." and the name still reads "Demo User".
4. Repeat with a new email, then with the three password fields. Expected: the same toast each time; logging out and back in with `demo123` still works.

**AC11 — demo can still use the features**
Still as the demo user: add an expense, edit it, delete it, set a monthly budget. Expected: each works with its usual green toast.

**AC12 — the demo banner**
1. As the demo user, open /profile. Expected at the top: "You're using the shared demo account. Profile settings are locked — create your own free account to try them." Click "create your own free account". Expected: the register page opens.
2. Log out, log in as any other account, open /profile. Expected: no banner.

**AC13 — normal users can still edit their profile**
As a non-demo user: change the name (expect "Profile updated."), change the password (log out and back in with the new one).

**AC14 — production refuses to start without a secret key**
In the second terminal run:
`SPENDLY_DB=/tmp/spendly-x.db RAILWAY_ENVIRONMENT=test SECRET_KEY= venv/bin/python -c "import app"`
Expected: it ends with `RuntimeError: SECRET_KEY must be set in production`.
Then run `SPENDLY_DB=/tmp/spendly-x.db SECRET_KEY=abc RAILWAY_ENVIRONMENT=test venv/bin/python -c "import app; print('ok')"`. Expected: prints `ok`.
(`SPENDLY_DB=/tmp/spendly-x.db` makes these commands use a throwaway database instead of your real `database.db`.)

**AC15 — cookie flags**
Run: `SPENDLY_DB=/tmp/spendly-x.db venv/bin/python -c "import app; c=app.app.config; print(c['SESSION_COOKIE_HTTPONLY'], c['SESSION_COOKIE_SAMESITE'], c['SESSION_COOKIE_SECURE'])"`
Expected: `True Lax False` (locally). With `SECRET_KEY=abc RAILWAY_ENVIRONMENT=test` added in front, expected `True Lax True`.

**AC16 / AC17 — session reset and permanence**
These are covered by the automated tests (`/test-feature 10-security-and-reliability`). To see it by hand: register a new account, then DevTools → Application → Cookies → `session`: the **Expires** column shows a date about 31 days ahead (not "Session").

**AC18 / AC19 / AC19b — IST dates**
Covered by the automated tests, which fake the clock. By hand: after 00:00 IST but before 05:30 IST, register a new account; the "Showing" line on /profile shows **today's** IST date, not yesterday's.

**AC20 — all tests pass**
Run: `venv/bin/python -m pytest -q`
Expected last line: `N passed` with no `failed`.

**AC21 — tests never touch database.db**
This copies the project to a temporary folder **without** `database.db` and runs the tests there, so your real database is never moved or touched.
1. Stop the dev server (Ctrl+C in its terminal).
2. In the second terminal, from the project folder, run:
   `rm -rf /tmp/spendly-check && rsync -a --exclude database.db --exclude venv ./ /tmp/spendly-check/ && (cd /tmp/spendly-check && "$OLDPWD/venv/bin/python" -m pytest -q; ls database.db)`
3. Expected: the tests pass, and the last line says `ls: database.db: No such file or directory`.
4. Your real database is untouched: `ls database.db` in the project folder still prints `database.db`.

**AC22 — CI**
After the branch is pushed: open https://github.com/shreyansh0714/expense-tracker/actions. Expected: a "tests" run for this branch with a green check mark.

**AC23 — index**
With the app started at least once, run: `sqlite3 database.db ".indexes expenses"`
Expected: `idx_expenses_user_date` is listed.

**AC24 — stale comment gone**
Run: `grep -n "students will implement" app.py`
Expected: no output.

**AC25 — docs updated**
Run: `grep -n "superseded by Spec 10" .claude/specs/03-login-and-logout.md` (expect several lines), `grep -n "csrf_post" .claude/agents/spendly-test-writer.md` (expect a line), `grep -n "POST /logout" .claude/PROGRESS.md` (expect a line).

## 10. End-to-End Verification

1. `venv/bin/python -m pytest -q` → 0 failures (AC20), with no `database.db` created in a clean checkout (AC21).
2. Run the app and walk the Manual Verification Guide AC2, AC6, AC9 and AC12. These four show the forgery block, the POST-only logout, the demo lock and the banner.
3. Push the branch → the GitHub Actions "tests" run is green (AC22).
4. After merge and redeploy (with `SECRET_KEY` confirmed on Railway): log in to the live site as the demo user, try to change the name → the demo toast appears; sign out with the nav button → back on the landing page.
