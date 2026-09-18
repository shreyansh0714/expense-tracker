# Spendly — Progress

Living status file: what's built, what's still open, what's deferred.
Moved out of `CLAUDE.md` to keep that file focused on *rules for working in
this repo* rather than *current status* — `CLAUDE.md` links here instead of
carrying this content itself. Updated automatically as work happens; no
need to ask before editing this file (unlike `CLAUDE.md` itself, which
still needs the developer's go-ahead for rule changes).

Each item below names the session (by date) and commit (short hash + one-
line message) it landed in, so you can `git show <hash>` to see exactly
what changed.

## Routes — implemented vs stub

The fastest way to know what's safe to build on vs. what's intentionally
unfinished. Flip a row to Implemented in the same commit that builds it.

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET/POST /register` | Implemented — Step 2, creates a user and starts a session |
| `GET/POST /login` | Implemented — Step 3, verifies email/password and starts a session |
| `GET /logout` | Implemented — Step 3, clears the session, redirects to `landing` |
| `GET /terms` | Implemented — renders `terms.html` |
| `GET /privacy` | Implemented — renders `privacy.html` |
| `GET/POST /profile` | Implemented — Steps 4-5, dashboard + edit modal |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |
| `database/db.py` | Implemented — Step 1 tables + helpers added by later steps |

**Do not implement a stub route unless the active task explicitly targets that step.**

## Progress, by Step

### Pre-Step scaffolding (2026-08-25 – 2026-08-31)

- [x] Initial repo, landing page hero/features/CTA, T&C + privacy pages,
      "how it works" video modal
      — `99638f6`, `8f14956`, `338f12e`, `5778576`, `a1e667d`

### Step 1 — Database Setup (2026-09-15)

- [x] `database/db.py`: `get_db`/`init_db`/`seed_db`, `users`/`expenses`
      tables, `PRAGMA foreign_keys = ON`, demo seed data
      — `19ed329` "database setup complete" (merged `a00c106`)
- [x] Project's `CLAUDE.md` written — `916d0f6`

### Step 2 — Registration (2026-09-16)

- [x] Custom slash commands scaffolded (`seed-user`, `seed-expense`, etc.)
      — `e61080c`
- [x] `GET/POST /register`: validation, password hashing, session start
      — `3c8be91` "registration feature implement" (merged `e46d0df`)

### Step 3 — Login / Logout (2026-09-16)

- [x] `GET/POST /login`, `GET /logout`; rules and spec-command updates
      — `713fdca` (merged `109f2ce`)
- [x] Manual verification pass; learning-notes artifact started
      — `caff9fc`

### Step 4 — Profile Page (2026-09-16)

- [x] `spendly-ui-polish` skill brief drafted — `b50f064`
- [x] `.claude/plans/` un-gitignored and existing plans committed
      — `bb1eddf`
- [x] Process conventions added (spec-interview split, mockup-content,
      explanation clarity, session scope) — `6646b34`
- [x] `spendly-ui-polish` skill built (tokens, textures, component→
      treatment table) — `8bd70d7`
- [x] Step 4 spec written, including backfilled read-only display content
      — `30fc79e`
- [x] Step 4 implementation plan written (+ later Revision section for the
      two-column layout) — `5803b1f`
- [x] Step 4 implemented: settings form, spend summary, category
      breakdown, recent activity, notes, paper-ledger styling applied
      — `3695935`
- [x] Merged to `main` via PR #5 (`b92fe1e`)
- [ ] Fix the concrete issues found in the 2026-09-16 subagent audit —
      see **Open Tasks** below. Audit's bottom line: the implementation is
      largely faithful to the spec/plan (layout, content, and styling all
      verified correct); the "missing lots of things" impression traces to
      a small number of specific bugs below, not a broad implementation
      failure — worth double-checking you weren't looking at a stale page
      load or your own account's data instead of the demo account.

### Step 5 — Profile Page Redesign (Dashboard + Edit Modal) (2026-09-17)

- [x] Backend: `get_monthly_transaction_count`, derived `top_category`
      — `5cf439c` "Add transaction count and top category to profile route"
- [x] Spec written (`.claude/specs/05-profile-page-redesign.md`), scoped
      to the dashboard restructure + edit-modal move only — Phase E
      (design-system doc rewrite) and Phase F (mockup + real paper-visual
      implementation) explicitly out of scope, tracked separately below
- [x] Implementation plan written (Design Plan + Tasks format, paired
      with the spec) — `.claude/plans/05-profile-page-redesign.md`
- [x] Dashboard restructure implemented: avatar header, 3 stat tiles
      (Total Spent + budget-used subtext, Transactions, Top Category),
      Recent Transactions table (Date/Description/Category pill/Amount),
      By Category card with proportional bars, edit-profile form moved
      into a modal with a crumple-open animation
      (`prefers-reduced-motion`-guarded), Notes card now renders in the
      typewriter font
- [x] Phase E: `spendly-ui-polish/references/design-system.md` (and
      `SKILL.md`'s workflow steps) rewritten from per-card paper
      treatments to the global-page-background/hand-drawn-border/
      sparing-tape-pin/Notes-as-sticky-note philosophy the developer
      described. `--sticky`/`--sticky-mint` tokens added to `:root` in
      `style.css`, closing that previously-tracked gap.
- [x] Phase F mockup: `frontend-design`-skill Artifact
      (`claude.ai/artifact/6tKfNrS2cKZddUUBzVqn3g`) applied the revised
      system to the profile page; developer reviewed, asked for more
      background crumple + visible fold lines + the Notes card attached
      to the header card's top-right corner, then approved.
- [x] Phase F implementation: `templates/profile.html` +
      `static/css/style.css` updated to match the approved mockup —
      page-level crumple + fold lines scoped to `.profile-section`
      (not global `body`), a shared `.hand-drawn` SVG-outline border
      (`feTurbulence`/`feDisplacementMap`) on the header, stat tiles,
      transactions table, and by-category card, each with a slight
      individual `.tilt-*` rotation, and Notes converted from an inline
      card into a `.notes-sticky` attached to the header card's corner —
      small at rest, expands via `:focus-within` when the textarea is
      focused, content in `--font-type` (typewriter), not `--font-hand`.
      Old per-card system removed as dead code: `.paper-card` (+
      `.torn-top`/`.torn-both`/`.kraft`/`.notes-card`), `.paper-pin`,
      `.paper-tape`, `.pencil-tag`, `.paper-card-header`, `.paper-hole` —
      confirmed via grep that nothing else in the app referenced them.
- [ ] `--paper-stack-1`/`--paper-stack-2` tokens in `style.css` are still
      unused (the "paper-stack depth" technique they supported needed a
      torn card edge to sit behind, and torn edges are retired) — left
      declared rather than removed, low-priority cleanup.
- [ ] Live-browser verification — still not done, across two separate
      sessions of trying. Playwright's browser profile stayed locked by
      another process the entire time
      (`Browser is already in use for .../mcp-chrome-7272251`), for: the
      modal open/close, the crumple-open animation,
      `prefers-reduced-motion` behavior, the email-verification modal
      triggering from inside the edit-profile modal, the hand-drawn SVG
      borders actually rendering as intended, the Notes sticky note's
      `:focus-within` expand, and the page-level crumple/fold-line
      background. Everything is verified only via Flask test-client
      checks (200 status, correct markup present) and direct code
      review — see **Open Tasks** below.
- [ ] Full Validate (Manual Verification Guide) + `/test-feature` + `/code-review-feature` pass —
      deliberately deferred to a later, consolidated verification once
      Phase E/F's visual work also lands, per the developer's explicit
      choice this session (not run incrementally after each phase).

## Future Features

Deferred because they need infrastructure this project doesn't have yet,
or their own spec. Not stubs in `app.py` — tracked here so they aren't
lost. Move an entry out once it becomes a real numbered spec under
`.claude/specs/`.

| Feature | Why deferred | Needs |
|---|---|---|
| Playwright end-to-end tests + CI/CD pipeline | Explicitly future work per the developer (2026-09-17) — the project has Validate (manual), `/test-feature` (pytest via subagents) and `/code-review-feature` (security + quality subagents) so far | Its own spec — which flows/pages get e2e coverage, and what CI provider/pipeline to use |
| Budget threshold alerts (toast at 90% of budget consumed + audit log) | Needs expense-aggregation logic that belongs with the future Dashboard | Its own spec, including what "audit the logs" records and where |
| Real email-change verification (OTP to the new address) | Needs an actual email-sending mechanism + credential handling | Its own spec — `PROFILE_EMAIL_BYPASS_CODE` is the explicit non-production stand-in until then |
| Auto-calculated suggested monthly budget (from last 3 months of spending) | Was mockup flavor text on the paper-ledger moodboard, never a real requirement | Its own spec — in particular, behavior for an account with under 3 months of history |

## Open Tasks

Known, concrete issues in already-built work — not new features, things
to fix. Found via a 3-subagent audit on 2026-09-16
(`profile-page-gap-auditor`, `tooling-and-skill-auditor`,
`earlier-steps-auditor`), each independently reading the specs/plans
against the live code.

| Area | Issue | Kind |
|---|---|---|
| Profile page (`app.py:135`) | Monthly budget renders in scientific notation for values ≥ ₹1,000,000 (Python's `:g` format switches to exponent form, e.g. `1e+06`) — a real display bug | Bug |
| Profile page (`static/css/style.css`) | `.profile-card-title` applies italic to *every* card title, but `design-system.md`'s table only specifies italic for the reference/notes card specifically — may be an intentional broader reading of the Typography section, needs a judgment call | Needs a decision |
| `spendly-ui-polish` skill | The 3 saved eval prompts (`evals/evals.json`) have never actually been run — no results/workspace exist | Unverified |
| Profile page (Step 5 dashboard/modal + Phase F visual polish) | Modal open/close, the crumple-open animation, `prefers-reduced-motion` behavior, the nested email-verification-modal-from-inside-the-edit-modal flow, the hand-drawn SVG card borders, the page-level crumple/fold-line background, and the Notes sticky note's `:focus-within` expand are only verified via code review + Flask test-client checks — never exercised in a real browser (Playwright's browser profile stayed locked across every session this work touched) | Unverified |
| `verify` subagent | Dropped on 2026-09-19: `/test-feature` covers the automatable acceptance criteria and the manual Validate step covers visual ones. The TODO was removed from `CLAUDE.md` and `create-spec.md`. Revisit when Playwright lands | Resolved — not needed |
| `.claude/skill-briefs/spendly-ui-polish.md` | Stale scaffolding from before `skill-creator` ran — fully superseded by `.claude/skills/spendly-ui-polish/`, drifted out of sync with it. Safe-to-delete candidate | Cleanup |
| `.claude/specs/01-databse-setup.md` | §14 "Definition of Done" checklist still all unchecked `- [ ]`, never flipped after the work was done | Doc-only |
| `.claude/plans/01-database-setup.md` | Describes a verification script to run, but no pass/fail results were ever recorded | Doc-only |
| Step 2 (Registration) | No `.claude/plans/02-registration.md` exists at all — the only Step missing a plan file, breaking `create-spec.md`'s own plan-pairing convention | Missing doc |
| `.claude/specs/03-login-and-logout.md` | §8 Acceptance Criteria still all unchecked `- [ ]` in the spec itself, even though `.claude/plans/03-login-and-logout.md` documents completed manual verification with actual `curl` output — spec and plan are out of sync on completion status | Doc-only |
