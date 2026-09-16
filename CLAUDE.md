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

> ⚠️ **TODO — verify subagent, not yet built.** Once a spec's implementation
> plan finishes, verifying the feature against the spec's Acceptance
> Criteria / Manual Verification Guide must be delegated to a dedicated
> `verify` subagent — **the main agent must never self-verify.** This is a
> placeholder rule only: there is no `.claude/agents/verify.md` and no hook
> wiring it in automatically yet. Until that exists, the main agent should
> say so explicitly and ask the user to verify manually (using the spec's
> Manual Verification Guide — see "Spec verification convention" below)
> instead of quietly verifying itself. Update this note when the `verify`
> subagent and its hook are actually built.

## Learning notes artifact

The developer is building this project as a learning exercise and keeps a
living reference doc, **Spendly Field Notes**, for backend/Python/Flask
concepts they're new to (explained through what they already know —
React, Redux, JS, HTML/CSS, Git):

https://claude.ai/artifact/6vjCPWhWYkaTTQqTYzvqu3

- **Update it in place** (same URL) as the project grows or as new doubts
  come up in a session — don't create a new artifact. Read it first
  (`Artifact` action `read`), then republish with `url:` set to the link
  above, following the section template already established in the doc
  (prerequisite flag → why → analogy-first what → one concrete Spendly
  example → how it works → good practices → when to use/not → where
  else it shows up). Section 0 (project map) should get redrawn whenever
  a row in the "Implemented vs stub routes" table below actually changes.
- **Before re-explaining something from scratch in chat, check whether
  the artifact already covers it.** If it does, point the developer to
  that artifact section instead of retyping the explanation — the
  artifact is the durable copy; chat explanations aren't. Only add fresh
  chat explanation for something genuinely new, then fold it into the
  artifact per the update rule above.
- See the `spendly-beginner-teaching-style` memory file for the exact
  explanation pattern to follow, and `../prompt.md` (one level up, next
  to this project folder) for the full reusable process this artifact
  was built from.

## Spec verification convention

- The developer driving this project is a beginner and does not yet know how
  to verify acceptance criteria independently (e.g. reading a session
  cookie in DevTools, running a `curl`/`pytest` check, reading a server
  log). Every spec written by `/create-spec` must therefore include a
  **Manual Verification Guide** section directly below **Acceptance
  Criteria** — explicit, beginner-friendly, step-by-step instructions
  (exact UI paths, exact commands, exact expected output) for verifying
  *each* acceptance-criteria item by hand. See
  `.claude/commands/create-spec.md` for the section this produces.
- See the subagent policy above for who actually runs verification once an
  implementation is done — that's a separate, currently-unbuilt piece
  (the `verify` subagent), not this section.

## Spec interview convention

- `/create-spec`'s interview (Step 8) asks about editable/mutation content
  and read-only/display content as two separate questions, checks for any
  existing design mockup/prototype from earlier conversations before
  finalizing scope, and closes with a catch-all "anything else?" question.
  See `.claude/commands/create-spec.md` Step 8 for the full rule — added
  after the Step 4 (Profile page) spec initially missed its read-only
  display content (spend summary, category breakdown, notes) because the
  interview only asked about editable fields.

## Mockup content convention

- A design mockup/moodboard (e.g. the paper-ledger artifact
  `spendly-ui-polish` is locked to) shows *look*, not *content* — any text
  written on it is fake, placed there only to make the mockup look
  realistic. When applying visual polish from a mockup, copy its
  colors/spacing/typography/treatment; never copy its words onto a real
  page. Real page content always comes from the spec or the page's own
  data, never from a mockup's placeholder text. See
  `.claude/skills/spendly-ui-polish/references/design-system.md`'s "What
  this skill should never do" section for the full rule — added after the
  paper-ledger moodboard's fake "auto-calculated from last 3 months"
  caption and its two "Pinned" process-note stickies were nearly mistaken
  for real requirements on the Step 4 (Profile page) spec.

## Explanation & document clarity convention

- Never explain a decision, a gap, or "what changed" using a bare pointer
  like "this gap," "that issue," or "the problem above" and assume the
  reader already holds the reference in mind. Always restate, in plain
  words, exactly what's being pointed at — quote the actual source
  text/file/line where one exists.
- When the answer to a question is a set of yes/no or status items (e.g.
  "are these implemented?", "what changed?"), answer with a table —
  item → status → one-line reason — not a paragraph the reader has to
  parse to extract the answer.
- This applies everywhere the developer has to read and understand
  something Claude produced: chat replies, **and every section of a spec
  or plan** — not just the Manual Verification Guide, which already had
  to be this concrete by its own convention above.

  **Bad** (a real line from this project's history, flagged by the
  developer as unclear): *"That's a real gap — want me to add it now?"*
  — vague pointer, no restated reference, forces the reader to scroll back
  and guess which gap.

  **Good** (the corrected version the developer confirmed worked):
  *"Two mockup captions were fake demo text, not real features: 'auto-
  calculated from last 3 months' under the budget field, and the two
  'Pinned' stickies ('Beautify only — CSS + markup polish...', 'Read the
  spec first. Style second.'). Nothing today stops a future page-polish
  pass from copying that text onto a real page. Want me to add a rule
  preventing that — yes or no?"* — names the exact text, states the
  concrete risk in one sentence, ends with one direct question.

  **Bad** (status question answered as prose): *"Most of what you asked
  about is implemented — notes and the spend summary are done, though the
  transaction history part is more of a preview than a full history since
  that got scoped down earlier."*

  **Good** (same content, as a table):

  | Item | Implemented? |
  |---|---|
  | Personal notes section | Yes |
  | Monthly total spend | Yes |
  | Category breakdown | Yes |
  | Full transaction history | No — scoped down to a 5-item preview earlier |

- **Why:** added 2026-09-16 after the developer said, verbatim: "explain
  in simple and plain terms and also dont talk without any reference and
  assuming i will catch it." The corrected explanation (quoted text +
  concrete risk + single question) got the reply "this explanation was
  good and i was able to understand" — that's the calibrated bar for
  every explanation and every spec/plan section from here on, not just
  the one that prompted this rule.

## Session scope convention

- Don't bundle a whole page's worth of work into one uninterrupted
  implementation pass — layout, every piece of content, and full visual
  polish all at once. Build and get one piece reviewed before moving to
  the next.
- **Why:** the Step 4 (Profile page) implementation tried to do the
  two-column layout, every piece of read-only content (member-since,
  budget-vs-spent, category breakdown, recent activity, notes), *and* the
  full `spendly-ui-polish` visual treatment in one session. Result,
  confirmed by the developer directly on 2026-09-16: "the profile page ui
  is missing lots of things that we have decided and also the data is not
  rendered correctly on the page rn." Their own stated lesson: "never
  implement too many features all together in one session." See the
  Future Tasks entry below for the actual cleanup this now needs.
- **How to apply:** when a plan's Tasks checklist has several
  independent-ish pieces (e.g. structure, then content A, then content B,
  then visual polish), stop and show the developer what's built after
  each piece — or at minimum after structure and after content, before
  visual polish — rather than running the entire checklist end to end and
  presenting it all at once.

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

## Future Tasks / Features

<!-- Deferred during spec interviews because they need infrastructure this
     project doesn't have yet, or their own spec. Not stubs in app.py —
     just tracked here so they aren't lost. Remove an entry once it's been
     turned into a real numbered spec under .claude/specs/. -->

- **Profile page UI rework (not a new feature — finish Step 4 as spec'd).**
  Confirmed by the developer on 2026-09-16: the Profile page is still
  missing several elements already decided in
  `.claude/specs/04-profile-page.md` / `.claude/plans/04-profile-page.md`
  (the "Revision" section), and the data that does render on the page is
  incorrect. Needs another implementation pass, done in smaller pieces per
  the Session scope convention above rather than all at once: re-check
  every item in the spec's Acceptance Criteria and the plan's Design Plan
  against what's actually on the live page before considering Step 4 done.
  No new spec needed — this is finishing existing scope, not new scope.
- **Budget threshold alerts.** Surfaced during the Step 4 (Profile page)
  spec interview: once a user sets a monthly budget, warn them (a toast) at
  90% of it consumed, and audit-log the alert (message type, timestamp,
  user). Needs expense-aggregation logic that belongs with the future
  Dashboard feature — needs its own spec, including what exactly "audit the
  logs" should record and where those logs live.
- **Real email-change verification (OTP).** Surfaced during the Step 4
  (Profile page) spec interview: changing your account email should send a
  one-time code to the *new* address and require it back before the change
  takes effect. Needs an actual email-sending mechanism (SMTP or a service)
  and credential/config handling — needs its own spec. Until this exists,
  Step 4 uses a temporary, explicitly-non-production stand-in (an
  environment-variable bypass code) — see `.claude/specs/04-profile-page.md`.
- **Auto-calculated suggested monthly budget.** Surfaced from the original
  paper-ledger moodboard's profile-form mockup, which had a caption reading
  "auto-calculated from last 3 months" under the budget field — that
  calculation was never a real requirement and was deliberately excluded
  from the Step 4 implementation (the caption was mockup flavor text, not
  a decided feature). Worth considering for real later: suggest a monthly
  budget based on the average of the user's last 3 months of expenses.
  Needs its own spec — in particular, what happens for an account with
  less than 3 months of history.
