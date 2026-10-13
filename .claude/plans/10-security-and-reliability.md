# Plan 10 — Security & reliability basics

Spec: `.claude/specs/10-security-and-reliability.md` · Branch: `feature/security-and-reliability`
Once approved, this file is saved into the repo as `.claude/plans/10-security-and-reliability.md` (Task 0).
The overall roadmap stays in the local `.claude/plans/10-11-readme-roadmap.md`.

**Live-checklist rule:** immediately after finishing each task, re-open this plan file and tick its box. Don't batch updates, and don't rely on memory.
**Verify rule:** after each checkpoint, a separate verifier subagent checks the work before it's shown to the developer.

## Context
A six-reviewer portfolio review found basic gaps:
- no CSRF protection
- a GET logout
- a writable shared demo account
- an unsafe secret-key fallback
- a test suite that fails on `main` and writes to the real `database.db`
- UTC/IST date bugs
- no CI

Spec 10 groups the fixes into one feature. The developer chose:
- 4 checkpoints, reviewing after each
- the demo banner reuses the `.range-note` style
- Sign out stays hidden on phones, as it is today

---

## Design Plan

### A. Test isolation and IST dates (checkpoint A)
- **`SPENDLY_DB`:** in `database/db.py`, `DB_PATH = os.environ.get("SPENDLY_DB", "database.db")`. Its default keeps Railway's start command (`ln -sf /data/database.db database.db`) working.
- **conftest:** sets `os.environ["SPENDLY_DB"]` to a module-level temp file (`tempfile.mkstemp`) **before** `from app import app`. It then asserts `db.DB_PATH != "database.db"`. The per-test `monkeypatch` to `tmp_path/"test.db"` stays as it is. The assert is checked at import time, before any monkeypatch runs, so it really proves the env var worked.
- **IST:** `IST = timezone(timedelta(hours=5, minutes=30))` and `today_ist()` go in `database/db.py`, because `seed_db` needs them and `db.py` can't import `app`. `app.py` does `from database.db import ..., IST, today_ist`.
  - `today_ist()` replaces `date.today()` at `app.py:342/385/504/553` and `db.py:94`.
  - `local_time()` changes `.astimezone()` to `.astimezone(IST)`.
  - Signup date (`app.py:335-336`): `datetime.strptime(...).replace(tzinfo=timezone.utc).astimezone(IST).date()`.
- **Tests:**
  - test_09: its 19 `"2026-09-22"` literals plus `2026-09-01`/`2026-09-30` (`:149`, `:156-157`) become values computed from `today_ist()`, such as `today_ist().isoformat()` and the first/last day of the current month. That turns the 5 `TestProfileMarkup` failures green.
  - test_06 and test_06b: their ~34 `date.today()` calls become `today_ist()` imported from `database.db` (FR8.2). Their date literals that are only validation inputs (`test_06:352-357, :642`, `test_06b:410/413`) stay, because the calendar doesn't affect them.
- **Clock tests (FR8.3, AC18, AC19, AC19b):** monkeypatch `app.today_ist` (the name `app` imported, not `db.today_ist`), and set `created_at` with a direct `UPDATE` through `db.get_db()`. Both are approved exceptions in the spec.

### B. CSRF, logout and session safety (checkpoint B)
- **Token:** `_csrf_token()` returns `session.setdefault("csrf_token", secrets.token_hex(32))`, exposed to templates by `@app.context_processor` as `csrf_token`.
- **Check:** one `@app.before_request`. On POST, compare `request.form.get("csrf_token", "")` with `session.get("csrf_token", "")` using `hmac.compare_digest`; a missing session token counts as a fail. On failure:
  - `flash("Your form expired. Please try again.", "error")`
  - redirect to a **safe referrer**: `ref = request.referrer or ""`, used only if `urlparse(ref).netloc == request.host`, else `url_for("landing")`. The `or ""` avoids comparing bytes with a string when no Referer is sent
  - `urllib.parse` is stdlib, so no new package (FR1.5)
- **Hidden inputs:** a hidden `csrf_token` input in the 7 existing POST forms: `login.html:20`, `register.html:20`, `add_expense.html:43/46`, `profile.html:71/289/339`.
- **Logout:**
  - `@app.route("/logout", methods=["POST"])` with `session.clear()`; GET then gets 405 automatically.
  - `base.html:32` becomes `<form method="post" action="{{ url_for('logout') }}" class="nav-logout">` + token + `<button type="submit" class="nav-link-button">Sign out</button>`.
  - A new `/* --- Nav logout button --- */` block in `style.css` resets the button (background none, border 0, padding 0, font/colour inherited from `.nav-links a`, cursor pointer) using existing tokens only.
  - The mobile rule at `style.css:1249` gets `.nav-links .nav-logout` added, so the button stays hidden on phones like today.
- **Secret and cookies:** right after `app = Flask(...)`:
  - `IS_PRODUCTION = bool(os.environ.get("RAILWAY_ENVIRONMENT"))`
  - if production and no `SECRET_KEY`: `raise RuntimeError("SECRET_KEY must be set in production")`
  - `app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=IS_PRODUCTION)`
- **Login and register:** `session.clear()`, then `session["user_id"] = ...`, then `session.permanent = True`.
- **Test helper (FR7):** `csrf_post(client, url, data=None, **kwargs)` in `conftest.py`. It writes a fresh token through `session_transaction()` right before each post, then posts with `csrf_token` merged into `data`.
  - All 39 `.post(` calls switch to it, including `auth_client` and test_09's `_register_and_login`.
  - `test_09:243`'s `client.get("/logout")` becomes `csrf_post(client, "/logout")`.
- **Ordering inside B:** the helper and the test updates land in the **same step** as the check, so the suite never goes red between tasks.

### C. Demo lock and banner (checkpoint C)
- `DEMO_EMAIL = "demo@spendly.com"` in `app.py`'s constants. `is_demo = user["email"] == DEMO_EMAIL`, using the `user` already loaded at `app.py:334`.
- **POST lock:** placed **after the CSRF check** (that runs first, in `before_request`) and before the field parsing at `:398`. If `is_demo`: flash the spec's exact demo message (category `error`) and `redirect(url_for("profile"))`.
- **Banner:** the GET render (`:389-396`) passes `is_demo`. `profile.html:21`, before the header card, shows `{% if is_demo %}<p class="range-note">…<a href="{{ url_for('register') }}">create your own free account</a>…</p>{% endif %}`, reusing the existing `.range-note` look.
- Budget and the add/edit/delete expense routes are untouched, so the demo user is allowed through them (FR3.3).
- **Tests:** call `db.seed_db()` on the temp DB to create the demo user (FR8.4 exception).

### D. CI, leftovers and docs (checkpoint D)
- **`.github/workflows/tests.yml`:**
  - runs on push and pull_request, `ubuntu-latest`
  - `actions/setup-python` with `3.13`, `pip install -r requirements.txt`, `python -m pytest -q`
  - `env: TZ: Asia/Kolkata`; no secrets
- **Index:** `CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date)` in `init_db()`.
- **Stale comment:** the banner at `app.py:325` gets renamed to the real section name, keeping the banner style.
- **Docs:**
  - spec 03 lines around 31/52/188-190/206 are marked "(superseded by Spec 10)" with the new behaviour
  - `spendly-test-writer.md` gets the `csrf_post` rule plus the FR8.3/FR8.4 exceptions
  - `CLAUDE.md`: the test-isolation sentence and the `conftest.py` tree line
  - `PROGRESS.md`: `POST /logout` at `:37` and the Known issues list from spec §4

### Reused rather than new
- `.range-note` styling (banner)
- `flash()` + toast rendering (`base.html:15-19`, `main.js:27-38`)
- `get_user_by_id` (demo check)
- `format_day` (unchanged)
- `db.get_db`, `db.seed_db` (tests)
- the existing `abort(404)` ownership logic (unchanged)

---

## Tasks
- [x] 0. Save this plan as `.claude/plans/10-security-and-reliability.md`.

**Checkpoint A: test isolation + IST + green suite**
- [x] 1. `db.py`: `DB_PATH` from `SPENDLY_DB`; `IST` + `today_ist()`; seed dates use `today_ist()`.
- [x] 2. `conftest.py`: set `SPENDLY_DB` to a temp file before importing `app`; assert `DB_PATH != "database.db"`.
- [x] 3. `app.py`: import `IST`/`today_ist`; replace the 4 `date.today()` calls; `local_time` → IST; signup `created_at` UTC→IST.
- [x] 4. Tests: test_09 dates relative to `today_ist()`; test_06/06b `date.today()` → `today_ist()`. (New AC tests are written by `spendly-test-writer` in Task 22, per CLAUDE.md "Tests come from the spec, not the code" — changed 2026-10-02.)
- [x] 5. Run `venv/bin/python -m pytest -q` → 0 failures; isolation check in a temp copy without `database.db` (AC21).
- [x] 6. Verifier subagent → **show the developer checkpoint A**.

**Checkpoint B: CSRF + logout + session safety**
- [x] 7. `app.py`: `IS_PRODUCTION`, `SECRET_KEY` fail-fast, cookie config.
- [x] 8. `app.py`: CSRF token + context processor + `before_request` check with safe referrer; templates get hidden inputs in the 7 forms; `conftest.csrf_post` + every `.post(` in `tests/` switched, including the ones added in Task 4 (one step, so the suite stays green).
- [x] 9. Logout POST-only + `session.clear()`; nav form button + CSS reset + mobile rule; `test_09:243` → POST.
- [x] 10. Login/register: `session.clear()` + `session.permanent = True`.
- [x] 11. Existing suite green after B. (New tests for AC1–AC8, AC3b, AC14–AC17 come from `/test-feature` in Task 22.)
- [x] 12. Verifier subagent → **show the developer checkpoint B**.

**Checkpoint C: demo lock + banner**
- [x] 13. `app.py`: `DEMO_EMAIL`, `is_demo`, POST lock with the exact toast; `is_demo` passed to GET render.
- [x] 14. `profile.html` banner (reusing `.range-note`) + link to register.
- [x] 15. Existing suite green after C. (AC9–AC13 tests come from `/test-feature` in Task 22.)
- [x] 16. Verifier subagent → **show the developer checkpoint C**.

**Checkpoint D: CI + leftovers + docs**
- [x] 17. `.github/workflows/tests.yml`.
- [x] 18. `init_db` index; rename the stale banner comment.
- [x] 19. Docs: spec 03 superseded lines, `spendly-test-writer.md`, `CLAUDE.md` test-isolation + `conftest.py` lines, `PROGRESS.md` route row + Known issues.
- [x] 20. Full suite green; read-only index check `sqlite3 database.db ".indexes expenses"` (AC23); verifier subagent → **show the developer checkpoint D**.

**SDD finish**
- [x] 21. Developer runs the spec's Manual Verification Guide (Validate).
- [x] 22. `/test-feature 10-security-and-reliability`.
- [x] 23. `/code-review-feature 10-security-and-reliability`.
- [ ] 24. Show the commit message and file list → explicit yes → commit (no Claude attribution) → push → PR → CI green (AC22).
- [ ] 25. After merge: Field Notes sections (CSRF + POST logout, cookie flags + secret keys, date-proof tests, CI, demo account) and the redrawn section 0 map; verifier before publishing.

## Explicitly out of scope
These are per spec §6:
- a `@login_required` refactor
- rate limiting, gunicorn, storing money as paise, per-user timezones, email OTP
- automatic demo reset
- changing the session lifetime
- README changes, including the CI badge
- Spec 11 display fixes
- new tests for Steps 2, 3, 7 and 8

## Verification
Use the spec's own §8 Acceptance Criteria (AC1–AC25, AC3b, AC19b), §9 Manual Verification Guide and §10 End-to-End Verification. Each checkpoint also gets a separate verifier subagent before it's shown.

## Review follow-up (2026-10-14, developer chose "Do #1, defer #2 and #3")
Code review: APPROVED WITH SUGGESTIONS, 0 security findings.
- [x] R1. Re-wrapped the `csrf_post(...)` calls (32 calls) in the test files to the normal multi-line style. Whitespace only.
- [x] R2. Added 2 Known-issue rows to `.claude/PROGRESS.md`: `profile()` builds the dashboard before refusing a demo save; `today_ist()`/`IST` sit in `db.py`.
- [x] R3. Full suite green + verifier confirms.
- [ ] R4. Task 24: commit, push, PR, CI green.
