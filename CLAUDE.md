# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

"Spendly" is a Flask expense tracker being built incrementally as a step-by-step learning exercise (numbered "Steps", e.g. "Step 1 — Database Setup"). It is not a finished product — large parts of the backend are deliberate stubs waiting on later steps. The goal when working here is to implement the *current* step correctly, not to fast-forward the whole app.

## Architecture

```
expense-tracker/
├── app.py                  # Single Flask module — all routes live here (no blueprints, no app factory)
├── requirements.txt        # flask, werkzeug, pytest, pytest-flask
├── database/
│   ├── __init__.py         # empty — makes `database` a package
│   └── db.py                # STUB — sole data-access layer (get_db/init_db/seed_db), raw sqlite3
├── templates/
│   ├── base.html            # Shared layout: nav, footer, font links, {% block title/head/content/scripts %}
│   ├── landing.html          # extends base.html — marketing/home page
│   ├── login.html            # extends base.html — sign-in form (renders only, no POST handler yet)
│   ├── register.html         # extends base.html — sign-up form (renders only, no POST handler yet)
│   ├── terms.html            # extends base.html — static legal copy
│   └── privacy.html          # extends base.html — static legal copy
└── static/
    ├── css/style.css         # Single stylesheet, CSS custom properties for design tokens
    └── js/main.js            # Vanilla JS, no build step, no framework
```

Where things belong:
- New routes → `app.py` only, no blueprints
- DB logic → `database/db.py` only, never inline in a route
- New pages → new `.html` file extending `base.html`
- Page-specific styles → a new `.css` file (once one is needed), not inline `<style>` tags — `style.css` stays the shared/global sheet

Flow: request → route function in `app.py` → (once implemented) calls `database/db.py` for data → `render_template()` renders a template that extends `base.html` → template pulls in `static/css/style.css` and `static/js/main.js` via `url_for`.

- **No ORM, no blueprints, no app factory, no build tooling.** Everything is intentionally flat and explicit — don't introduce these patterns for a Flask app this small.
- `database/db.py` is meant to be the *only* place that touches `sqlite3`. Routes call `get_db()`; they never open a connection directly.
- Templates always extend `base.html`; page-specific markup goes in `{% block content %}`, page-specific `<head>` additions in `{% block head %}`, page-specific scripts in `{% block scripts %}`.

## Code style

- **Python**: 4-space indent, `snake_case` for functions/variables. Route sections in `app.py` are separated with banner comments:
  ```python
  # ------------------------------------------------------------------ #
  # Routes                                                              #
  # ------------------------------------------------------------------ #
  ```
  Keep this banner style when adding new sections rather than inventing a new comment convention.
- **HTML/Jinja**: 4-space indent. Always use `url_for('endpoint')` for internal links — never hardcode a path like `/login`. Template files stay thin; logic belongs in the route, not the template.
- **CSS**: kebab-case, component-part class names (`auth-title`, `form-input`, `btn-submit`, `nav-cta`) — not BEM, not utility classes. All colors/fonts/spacing constants go through the CSS custom properties defined in `:root` in `style.css` (`--ink`, `--paper`, `--accent`, `--radius-md`, etc.) — never hardcode a hex color or px value that already has a token. New sections of the stylesheet get the same `/* --- Section --- */` banner-comment treatment as `app.py`.
- **JS**: vanilla, no framework, wrapped in an IIFE per feature block (see `main.js`). Guard on missing DOM elements (`if (!el) return;`) rather than assuming markup exists.
- **DB queries**: always use parameterized queries (`?` placeholders) — never build SQL with f-strings or string concatenation.
- **Error handling**: once a route is actually implemented, use `abort()` for HTTP errors, not a bare `return "error string"`. (This doesn't apply to the current placeholder stubs — those intentionally return plain strings until their step is built.)

## Preferred libraries

Only what's already in `requirements.txt` — don't add new dependencies without a clear reason:

- **Flask** — web framework
- **Werkzeug** — comes with Flask; use its `generate_password_hash` / `check_password_hash` for auth (Step 3+) instead of writing custom hashing or adding `bcrypt`/`passlib`
- **sqlite3** (stdlib) — the only database layer; no SQLAlchemy or other ORM
- **pytest** + **pytest-flask** — testing

**Tech constraints**: Flask only (no FastAPI/Django) · SQLite only (no Postgres, no ORM) · vanilla JS only (no React, no jQuery, no npm packages) · no new pip packages unless explicitly told otherwise.

## Custom slash commands (`.claude/commands/*.md`)

- A `` ```! `` block (or inline `` !`command` ``) runs **automatically before Claude is even involved, with no permission prompt** — it's dynamic-context injection, meant only for read-only lookups (a `git diff`, a `SELECT` query), never for anything that mutates state.
- Any command that writes data (`INSERT`/`UPDATE`/`DELETE`, file writes, etc.) must NOT put that action in a `!` block. Instead, write the script in a plain fenced code block and instruct Claude to run it itself via its own Bash tool call — so it goes through normal tool permissions like any other write.
- See `.claude/commands/seed-expense.md` for the pattern: the read-only `SELECT id, name, email FROM users` list uses `` !`sqlite3 ...` ``, while the `INSERT INTO expenses` script is a plain ` ```bash ` block Claude is told to run itself.

## Verification hygiene

- If Claude runs a command that writes data (`database.db`, or any file) to verify it works — rather than the user invoking it themselves — Claude must tell the user it did this, since it produces real rows/files indistinguishable from the user's own.
- Claude must then clean up whatever that verification run created (delete the test rows/files) before finishing the task, not leave them for the user to discover later.

## Subagent policy

- Use a built-in `Explore` subagent for codebase exploration before implementing any non-trivial new feature.
- Use a subagent to verify test results after an implementation, once tests exist.
- When asked to plan, delegate codebase research to a subagent before presenting the plan.
- Use the built-in `Plan` subagent when working in plan mode.

## Plan checklists

- Every implementation plan (Plan Mode output, or a plan written under `.claude/plans/`) must include a literal `- [ ]` checklist of concrete steps, not just prose — this is the drift guard so progress survives a mid-task compaction or context reset: re-reading the plan file tells you exactly what's done vs. pending without re-deriving it from a diff.
- Check boxes off as each step is *actually* completed, not in advance.
- Once implementation finishes, leave the checklist in place (all boxes checked) rather than deleting it — it doubles as a record of what was done, matching the pattern in `.claude/plans/01-database-setup.md` and `.claude/plans/03-login-and-logout.md`.

## Commands

Run from `expense-tracker/` with the venv active:

```bash
source venv/bin/activate
python app.py                       # dev server at http://localhost:5001 (debug=True)
pytest                              # run tests (pytest-flask installed; no tests exist yet)
pytest tests/test_x.py::test_name   # run a single test, once tests exist
pytest -k "test_name"               # run a single test by name/keyword
pytest -s                           # run tests with print output visible
```

No lint/format tooling is configured — don't assume `black`/`flake8`/`ruff` are available.

## Critical rules

- **Do not implement a stub route or function unless the active task explicitly asks for it.** Jumping ahead to a later Step breaks the incremental-learning structure of this project.
- **Never bypass `database/db.py`.** No inline `sqlite3.connect()` calls in `app.py` or elsewhere.
- `database/db.py` is implemented (`get_db`/`init_db`/`seed_db`, `users`/`expenses` tables) — `init_db()` and `seed_db()` run at app startup in `app.py`, creating `database.db` if it doesn't exist.
- **SQLite foreign keys are off by default** — `get_db()` must run `PRAGMA foreign_keys = ON` on every connection it returns.
- `app.run(debug=True, port=5001)` — debug mode is on, and the app runs on **port 5001**, not Flask's default 5000; don't change either. Treat any code path as visible in tracebacks — don't hardcode secrets into `app.py`.
- Passwords must go through Werkzeug's hashing helpers once auth is implemented — never store or compare plaintext passwords.
- Keep route logic in `app.py` thin; don't scatter data-access code across templates or static JS.
- Once a stub route's step is implemented, it should render a template — don't leave it returning a raw string.
- After implementing and verifying a stubbed feature, **ask the user** whether to update the "Implemented vs stub routes" table below — don't edit it unprompted, don't skip asking.

## Implemented vs stub routes

<!-- This table is the fastest way to know what's safe to build on vs. what's intentionally unfinished.
     After implementing AND verifying a stubbed feature, ASK the user whether to update this table —
     never edit it unprompted, and never leave it silently stale either. -->

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET/POST /register` | Implemented — renders `register.html`, POST creates a user and starts a session |
| `GET/POST /login` | Implemented — renders `login.html`, POST verifies email/password and starts a session |
| `GET /terms` | Implemented — renders `terms.html` |
| `GET /privacy` | Implemented — renders `privacy.html` |
| `GET /logout` | Implemented — clears session, redirects to `landing` |
| `GET /profile` | Stub — Step 4 |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |
| `database/db.py` (`get_db`, `init_db`, `seed_db`) | Implemented — Step 1 (`users`/`expenses` tables, `PRAGMA foreign_keys = ON`, demo seed data) |

**Do not implement a stub route unless the active task explicitly asks for that step.**
