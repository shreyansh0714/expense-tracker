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
│   └── db.py                # sole data-access layer (get_db/init_db/seed_db + query helpers), raw sqlite3
├── templates/
│   ├── base.html            # Shared layout: nav, footer, font links, {% block title/head/content/scripts %}
│   ├── landing.html          # extends base.html — marketing/home page
│   ├── login.html            # extends base.html — sign-in form
│   ├── register.html         # extends base.html — sign-up form
│   ├── profile.html          # extends base.html — profile dashboard
│   ├── terms.html            # extends base.html — static legal copy
│   └── privacy.html          # extends base.html — static legal copy
├── static/
│   ├── css/style.css         # Single stylesheet, CSS custom properties for design tokens
│   └── js/main.js            # Vanilla JS, no build step, no framework
├── tests/
│   ├── conftest.py           # shared fixtures: `client`/`auth_client` on a throwaway DB (never database.db)
│   └── test_<spec-name>.py   # one file per spec, written by /test-feature
└── .claude/
    ├── specs/                # one spec per step (/create-spec)
    ├── plans/                # one plan per spec (/implement-plan)
    ├── commands/             # slash commands (see "Commands" below)
    ├── agents/               # the 5 project subagents (see "Subagent policy")
    └── PROGRESS.md           # route status, future features, known issues
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

## Moving content between files

1. Add the content at the new place first.
2. `grep` the new file for the section heading to confirm it's there.
3. Only then delete it from the old place and write the pointer, in the
   same commit.

Never write "X lives in file Y" without that `grep` passing.

- **Why:** commit `01a61ae` (2026-09-17) deleted the "Implemented vs stub
  routes" table from this file and wrote "Route-by-route implemented/stub
  status lives in `.claude/PROGRESS.md`" — but the table was never added
  there. It stayed missing until the developer noticed on 2026-09-19.

## Verification hygiene

- If Claude runs a command that writes data (`database.db`, or any file) to verify it works — rather than the user invoking it themselves — Claude must tell the user it did this, since it produces real rows/files indistinguishable from the user's own.
- Claude must then clean up whatever that verification run created (delete the test rows/files) before finishing the task, not leave them for the user to discover later.

## Subagent policy

- Use a built-in `Explore` subagent for codebase exploration before implementing any non-trivial new feature.
- When asked to plan, delegate codebase research to a subagent before presenting the plan.
- Use the built-in `Plan` subagent when working in plan mode.
- **The main agent never self-verifies a feature.** After Build, the
  project's own subagents do the checking, always through their slash
  command (see "Spec-Driven Development (SDD) workflow" below):

| Subagent (`.claude/agents/`) | Launched by | Job | Tools |
|---|---|---|---|
| `spendly-test-writer` | `/test-feature` step 1 | Writes `tests/test_<spec-name>.py` from the spec only | Read, Edit, Write, Grep, Glob |
| `spendly-test-runner` | `/test-feature` step 2 | Runs that one file with `venv/bin/python -m pytest`, diagnoses failures | Read, Bash, Grep |
| `spendly-security-reviewer` | `/code-review-feature` (parallel) | Security findings tagged Critical/High/Medium/Low — any finding blocks the commit | Read, Grep, Glob |
| `spendly-quality-reviewer` | `/code-review-feature` (parallel) | Project-rule and maintainability review, ends with a verdict | Read, Grep, Glob |
| `explorer` | `/explorer` (start of a session) | Read-only orientation: reads CLAUDE.md, PROGRESS.md, memory, latest spec/plan, git state, and returns one briefing. Never edits anything | Read, Grep, Glob, Bash (read-only git only) |

- Subagent files load when a session starts. After adding or editing one,
  restart the session (`/exit`, then `claude --continue`) before relying on it.
- There is no separate `verify` subagent: `/test-feature` covers what can
  be checked automatically, and the developer's Manual Verification Guide
  pass covers what has to be seen. Revisit once Playwright gives an agent
  a real browser.

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
  a row in the "Routes — implemented vs stub" table in `.claude/PROGRESS.md`
  actually changes.
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
- The Manual Verification Guide is the "Validate" step of the SDD workflow
  below; `/test-feature` and `/code-review-feature` run after it.

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

## plain-brief keyword

- When the developer types `/plain-brief` **or just writes "plain-brief"
  in chat**, re-explain the latest report/status (or the named topic) in
  the plain-brief format. Full definition + Bad/Good example:
  `.claude/commands/plain-brief.md`. The 5 parts:
  1. **Where we are** — the feature in plain words, the SDD step, what
     just ran and why.
  2. **Who's who** — one plain line for every function, file, subagent,
     AC/FR number named.
  3. **Before/after** — what the spec requires (quoted), what the code
     did, what the user would actually see.
  4. **Status table** — item → status → one-line reason.
  5. **One direct question** at the end.
- Use this format by default for any report that follows long or
  background work (test runs, reviews, multi-agent tasks), even without
  the keyword.
- **Why:** added 2026-09-19. After a long run of subagent work, a
  code-review report named `resolve_date_range`, `format_day`, reviewer
  subagents and AC numbers with no reminder of what any of them were.
  The developer, verbatim: "its like running an organization and as a
  owner or boss , i cant remember every function and every single peice
  of code and there reference ... you just made me frustated." The
  corrected briefing followed the 5 parts above.

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

## Spec-Driven Development (SDD) workflow

The developer's own working pattern for this project, run once per feature
(one feature = one branch = one PR):

```
1. Git start    git switch main → git pull origin main → git checkout -b feature/<name>
2. SDD          Spec → Review → Design → Review → Tasks → Build → Validate
                (/create-spec)          (/implement-plan)        (Manual Verification Guide)
3. Testing      /test-feature <spec-name>
                  spendly-test-writer  → writes tests/test_<spec-name>.py from the spec only
                  spendly-test-runner  → runs it, diagnoses failures → final summary
4. Self review  /code-review-feature <spec-name>
                  spendly-security-reviewer ┐ run in parallel on `git diff main`
                  spendly-quality-reviewer  ┘ + new untracked files → unified report
5. Git finish   flip the feature's row in PROGRESS.md's route table (Stub → Implemented)
                → git commit → git push origin feature/<name> → create & merge PR
                → git switch main → git pull → git branch -d feature/<name>
```

Each step must pass before the next one starts: failing tests go back to
Build; a CHANGES REQUESTED review goes back to Build, then re-run Testing
and Self review. Never commit (step 5) with failing tests or a CHANGES
REQUESTED verdict.

**Interview depth for spec/skill/command creation.** These three artifact
types lock in decisions for a long time, so under-asking is expensive —
confirmed by this session's own failure: the Step 4 interview asked a
handful of questions and stopped, and the Profile page came out missing
several elements the developer had already decided on. No fixed question
count, but bias toward asking more, and run through this checklist before
considering the interview done: edge cases, error handling, scope
boundaries, naming/placement, and data shape. This standard applies to
creating spec/skill/command files specifically — a small fix or tweak
doesn't need the same interview depth.

**The three checks after Build** (not retroactive — already-shipped steps
aren't reopened to add them):

| Check | Who runs it | What it catches | Blocks commit when |
|---|---|---|---|
| Validate | The developer, by hand, using the spec's Manual Verification Guide | Anything you have to see: layout, modals, animations | Any step doesn't match its expected output |
| `/test-feature` | `spendly-test-writer` + `spendly-test-runner` | Behavior the spec promises: status codes, redirects, validation, DB side effects | Any test fails |
| `/code-review-feature` | `spendly-security-reviewer` + `spendly-quality-reviewer` | Security holes and project-rule breaks in the changed code | Verdict is CHANGES REQUESTED (any security finding at all, or a quality project-rule break) |

- **Tests come from the spec, not the code.** The test-writer never reads
  `app.py` or `database/` — a test copied from the code would pass even
  when the code is wrong. There is no pre-test interview: when the spec
  leaves a detail out, the writer outputs `SPEC GAP: <what's missing>`
  instead of guessing, and those lines are shown to the developer in the
  `/test-feature` report. Fix the spec, then re-run.
- **Tests never touch the real `database.db`.** `tests/conftest.py`
  swaps `database.db.DB_PATH` to a throwaway file per test (pytest's
  `monkeypatch` + `tmp_path`) and provides the shared `client` and
  `auth_client` fixtures. Test files use these; they never define their own.
- Alongside the checks, explicitly confirm the finished implementation
  matches what the developer actually asked for — not a feature Claude
  quietly built instead because it misread the intent. Ask directly if
  there's any doubt; don't assume a technically-passing test means the
  right thing got built.
- Playwright end-to-end tests and a full CI/CD pipeline are explicitly
  future work — tracked in `.claude/PROGRESS.md`'s Future Features table.

## Plan checklists

- Every implementation plan (Plan Mode output, or a plan written under `.claude/plans/`) must include a literal `- [ ]` checklist of concrete steps, not just prose — this is the drift guard so progress survives a mid-task compaction or context reset: re-reading the plan file tells you exactly what's done vs. pending without re-deriving it from a diff.
- Check boxes off as each step is *actually* completed, not in advance.
- Once implementation finishes, leave the checklist in place (all boxes checked) rather than deleting it — it doubles as a record of what was done, matching the pattern in `.claude/plans/01-database-setup.md` and `.claude/plans/03-login-and-logout.md`.

## Commands

Run from `expense-tracker/`. Always run pytest through the venv's Python
(`venv/bin/python -m pytest`) — a fresh shell, including a subagent's,
doesn't have the venv active:

```bash
source venv/bin/activate
python app.py                                        # dev server at http://localhost:5001 (debug=True)
venv/bin/python -m pytest                            # run all tests
venv/bin/python -m pytest tests/test_x.py -v         # run one test file
venv/bin/python -m pytest tests/test_x.py::test_name # run a single test
venv/bin/python -m pytest -k "test_name"             # run tests by name/keyword
venv/bin/python -m pytest -s                         # run tests with print output visible
```

Workflow slash commands (`.claude/commands/`), in the order the SDD
workflow uses them:

| Command | What it does |
|---|---|
| `/create-spec` | Syncs with main, creates the feature branch, writes `.claude/specs/<NN>-<name>.md` |
| `/implement-plan` | Turns a spec into a plan with a Design Plan and a `- [ ]` Tasks checklist |
| `/test-feature <spec-name>` | Writes tests from the spec, runs them, reports pass/fail + any `SPEC GAP:` lines |
| `/code-review-feature <spec-name>` | Parallel security + quality review of `git diff main` and new files, one unified verdict |
| `/seed-user`, `/seed-expense` | Add dummy data to `database.db` for manual testing |
| `/explorer` | Start-of-session orientation: launches the `explorer` subagent and shows its briefing |
| `/plain-brief [topic]` | Re-explains the latest report (or a topic) in the plain-brief format (see "plain-brief keyword" above) |

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
- **Do not implement a stub route unless the active task explicitly asks for that step.** Route-by-route implemented/stub status lives in `.claude/PROGRESS.md` (section "Routes — implemented vs stub"), not here.

## Project status

Route-by-route implemented/stub status, deferred future features, and
known open issues in already-built work all live in `.claude/PROGRESS.md`
— kept out of this file so `CLAUDE.md` stays focused on rules for working
in this repo rather than a snapshot of current status. That file updates
automatically as work happens (no need to ask first, unlike changes to
this file's actual rules).
