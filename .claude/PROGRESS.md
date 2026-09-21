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
| `GET/POST /profile` | Implemented — Steps 4-6 + 6b, dashboard + edit modal + date filter (`?range=…`), restructured to the single-flow layout |
| `POST /profile/budget` | Implemented — Step 6 Revision 1, saves/removes the monthly budget (from the range+budget bar since Step 6b), redirects back to `/profile` with the current filter |
| `GET /analytics` | Implemented — Analytics "coming soon" page, login-required (redirects to `login`) |
| `GET/POST /expenses/add` | Implemented — Step 7, add-expense form + this month's budget line, login-required; saves and redirects to `/profile` with a toast + highlighted row |
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

### Step 6 — Date Filter on the Profile Dashboard (2026-09-19)

- [x] Spec `.claude/specs/06-date-time-filter.md` + plan
      `.claude/plans/06-date-time-filter.md` written (branch
      `feature/date-time-filter`)
- [x] Filter bar on `/profile` only: This month / Last month / Last 3 months /
      All time + native From/To date boxes; stat tiles, Recent Transactions,
      By Category all follow the chosen range; error messages + "records
      begin" notes for custom ranges; Month-by-month budget table for
      multi-month ranges; styles in new `static/css/profile.css`
- [x] `/test-feature`: 32/32 pass (`tests/test_06-date-time-filter.py`)
- [x] `/code-review-feature`: first pass CHANGES REQUESTED (budget table
      shown for a range entirely before the user's records, up to 23,989
      rows) → fixed → re-review APPROVED (security: no findings; quality:
      APPROVED). Deferred suggestions logged in **Open Tasks** below
- [x] Revision 1 (2026-09-20), from the developer's manual check + the two
      infographics in `static/images/`: monthly-budget card on `/profile`
      (add / edit / remove, via the new `POST /profile/budget`), budget field
      removed from the edit-profile popup, active-range pill, Indian money
      grouping everywhere (`inr` Jinja filter, `₹12,34,567.50`), boxed
      budget table with a light-green header, redesigned filter bar,
      click-anywhere-to-open the date picker (`static/js/main.js`)
- [x] Revision 1 checks: `/test-feature` 45/45 pass; `/code-review-feature`
      → security had one Low finding (the `inr` filter crashed on `None` /
      non-numeric input) which was fixed and confirmed closed, quality
      APPROVED WITH SUGGESTIONS (suggestions applied: `POST /profile/budget`
      added to the route table, stylesheet banner updated, stale money-format
      notes corrected)
- [x] Developer's Manual Verification Guide pass (Validate) — confirmed by
      the developer on 2026-09-20
- [x] Commit, push, PR, merge — `2fb0571` "implement 06 feature
      date-time-filter , add the monthly budget button", merged to `main`
      on 2026-09-20 (`4d724ae`)

### Step 6b — Profile Dashboard Restructure (2026-09-20)

Driven by two infographics added to `static/images/`
(`profile-dashboard-structure-infographic.png`,
`profile-dashboard-before-after-infographic.png`). Spec
`.claude/specs/06b-profile-dashboard-restructure.md`, plan
`.claude/plans/06b-profile-dashboard-restructure.md`. Numbered `06b` rather
than `07` because Steps 7-9 are already reserved for the expense CRUD stubs.

- [x] Block order fixed: header → filter row → range+budget bar → 3 stat
      tiles → content grid → month-by-month budget table **last** (it used to
      split the page between the tiles and the grid)
- [x] `.filter-summary-row` replaced by `.range-budget-bar` — range summary
      left, budget control right. This is the order spec 06 FR9 asked for;
      the previous build had the two sides reversed
- [x] `templates/_icons.html` added: five Feather glyph macros (`edit`,
      `plus`, `wallet`, `list`, `heart`) as inline SVG. Replaces the bare
      `&#9998;` entities. No npm, no icon font, no CDN
- [x] Stat tiles restructured to text column + circular icon badge
- [x] "View all" link on Recent Transactions → `/analytics`
- [x] Seven `--cat-*` tokens: one colour per expense category, with
      `--cat-other` doubling as the fallback for free-text categories.
      Contrast measured — pill text 4.89-10.35:1, bar fills 3.09-8.91:1.
      `--cat-shopping` is `--accent-2` darkened to `#b8761f` because
      `#c17f24` measured 2.79:1 as a bar fill, under the 3:1 threshold
- [x] Empty states split in two: never-logged vs filter-matched-nothing
- [x] `spec 06` marked in 13 places where `06b` supersedes it (FR9's budget
      states, AC15/AC21/AC22, five verification rows)
- [x] **Hand-drawn card borders fixed** — see the Open Tasks entry; they had
      never rendered on any card but the page header

### Step 7 — Add Expense (2026-09-22)

Spec `.claude/specs/07-add-expense-button.md`, plan
`.claude/plans/07-add-expense-button.md`, branch `feature/add-expense-button`.

- [x] `database/db.py`: `insert_expense()`, shaped like `create_user`
- [x] `GET/POST /expenses/add`:
      - Fields: Amount (₹), Category (dropdown of the 7 categories in `EXPENSE_CATEGORIES`), Date (today or earlier), Description (optional, ≤200 chars)
      - The 7 exact error messages from spec FR6
      - Read-only line: "₹X of ₹Y used this month", or "No monthly budget set"
- [x] After saving: redirect to `/profile`, "Expense added." toast, and the new row fades from green once (`session["new_expense_id"]`, popped on the next load; no animation under `prefers-reduced-motion`)
- [x] Links to the page:
      - navbar **Add expense** (signed-in only)
      - **+ Add expense** next to "View all" on Recent Transactions
      - **Add your first expense** after both "You haven't logged any expenses yet." messages (supersedes spec 06b line 204)
- [x] ₹-prefix input styles moved from `profile.css` to `style.css`, shared by both pages
- [x] Existing suite as a regression check: 69 pass, 1 fails. The failing test fails with or without Step 7; it's the UTC-vs-local bug logged in **Open Tasks**
- [ ] Validate (Manual Verification Guide), `/test-feature`, `/code-review-feature`: **skipped by the developer's explicit choice (2026-09-22)**, committed and merged without them. Run them later to close this out

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
| Profile page (`app.py:135`) | Monthly budget renders in scientific notation for values ≥ ₹1,000,000 (Python's `:g` format switches to exponent form, e.g. `1e+06`) — a real display bug. **Resolved 2026-09-20 (Step 6 Revision 1):** the popup's budget box that used `:g` was removed; the new budget card formats through the `inr` filter in `app.py`, which uses Indian digit grouping, e.g. `₹10,00,000.00` | Resolved |
| Profile page (`static/css/style.css`) | `.profile-card-title` applies italic to *every* card title, but `design-system.md`'s table only specifies italic for the reference/notes card specifically — may be an intentional broader reading of the Typography section, needs a judgment call | Needs a decision |
| `spendly-ui-polish` skill | The 3 saved eval prompts (`evals/evals.json`) have never actually been run — no results/workspace exist | Unverified |
| Profile page (Step 5 dashboard/modal + Phase F visual polish) | Modal open/close, the crumple-open animation, `prefers-reduced-motion` behavior, the nested email-verification-modal-from-inside-the-edit-modal flow, the hand-drawn SVG card borders, the page-level crumple/fold-line background, and the Notes sticky note's `:focus-within` expand were only verified via code review + Flask test-client checks — never exercised in a real browser (Playwright's browser profile stayed locked across every session this work touched). **Partly resolved 2026-09-20 (Step 6b):** Playwright ran, and the first real browser pass immediately found the hand-drawn SVG card borders rendered on *no* card except the page header — `.hand-drawn > svg` sat behind each card's opaque `--paper-card` background, so the stroke was painted over. Fixed with `z-index: 2` + `overflow: visible` on the svg. Also confirmed in-browser: `prefers-reduced-motion` disables the sticky transition, the edit-profile modal opens, and the page-level crumple/grain renders. Still unverified: the crumple-open animation itself and the nested email-verification-modal flow | Partly resolved |
| `verify` subagent | Dropped on 2026-09-19: `/test-feature` covers the automatable acceptance criteria and the manual Validate step covers visual ones. The TODO was removed from `CLAUDE.md` and `create-spec.md`. Revisit when Playwright lands | Resolved — not needed |
| `.claude/skill-briefs/spendly-ui-polish.md` | Stale scaffolding from before `skill-creator` ran — fully superseded by `.claude/skills/spendly-ui-polish/`, drifted out of sync with it. Safe-to-delete candidate | Cleanup |
| `.claude/specs/01-databse-setup.md` | §14 "Definition of Done" checklist still all unchecked `- [ ]`, never flipped after the work was done | Doc-only |
| `.claude/plans/01-database-setup.md` | Describes a verification script to run, but no pass/fail results were ever recorded | Doc-only |
| Step 2 (Registration) | No `.claude/plans/02-registration.md` exists at all — the only Step missing a plan file, breaking `create-spec.md`'s own plan-pairing convention | Missing doc |
| Profile date filter (`templates/profile.html`, the "Showing 1 Jul 2026 – 19 Sep 2026" line above the stat tiles) | The template builds that date text itself (`range_start.day` + `strftime('%b %Y')`), while `app.py` already has a helper, `format_day()`, that makes the exact same "19 Sep 2026" text for the range notes. Two copies of one format means a future format change has to be made in both. Fix: pass ready-made `range_start_label`/`range_end_label` from `app.py`. Deferred from the Step 6 code review (2026-09-19), `spendly-quality-reviewer` suggestion 1. **Resolved 2026-09-20 (Step 6b, spec 06b FR9):** `profile()` now passes `range_start_label`/`range_end_label` built with `format_day()`, and `templates/profile.html` contains no `strftime` call | Resolved |
| `app.py` — `format_day()` helper (Step 6) | Name is vague: it returns a full date ("19 Sep 2026"), not just a day. Rename to e.g. `format_short_date`. Optional, from the Step 6 code review | Cleanup |
| `app.py` — `resolve_date_range()` (Step 6, turns `?range=…&start=…&end=…` into the dates the profile page shows) | Does 3 jobs in one ~58-line function: reads the preset, validates custom From/To dates, applies the "records begin" rules. Fine today; split into smaller helpers if another preset or rule is added. Optional, from the Step 6 code review | Cleanup |
| `app.py` — `profile()` route's `dashboard` dict (Step 6) | One dict holds both the date-filter values and unrelated profile values (`member_since`, `original_email`). Naming nit only, no bug. Optional, from the Step 6 code review | Cleanup |
| `/seed-expense` command (`.claude/commands/seed-expense.md`) | Creates expenses dated in the **future**. In `database.db` on 2026-09-19, user 6 has expenses up to 2026-09-23 and user 8 up to 2026-09-26. The Step 6 date filter never shows anything after today, so those seeded rows are invisible on `/profile`. Fix: cap seeded dates at today | Bug |
| Profile page (`templates/profile.html`, the Recent Transactions and By Category cards) | The same 4-line empty-state `{% if has_expenses %}` / `{% else %}` block is pasted twice, once per card. Both render the identical two FR8 messages, so a wording change has to be made in two places. Fix: extract a `{% macro empty_state() %}` alongside the existing `budget_form()` macro and call it from both cards. Raised by `spendly-quality-reviewer` in the Step 6b review (2026-09-20) as non-blocking — deferred rather than fixed because a third copy doesn't exist yet | Cleanup |
| `app.py` `profile()` — `created_at` vs `date.today()` (Step 6) | `users.created_at` is saved in **UTC** (`datetime('now')` in SQLite), but the profile page compares it with the **local** date (`date.today()`). Between 00:00 and 05:30 IST the UTC date is still yesterday, so a brand-new account's history start is a day early and the page reads "Showing 21 Sep 2026 – 22 Sep 2026" instead of "22 Sep – 22 Sep". Found 2026-09-22 00:46 IST: `test_06-date-time-filter.py::TestHistoryStartAdjustment::test_showing_line_for_fresh_user_starts_at_signup_date` fails at that hour, with or without the Step 7 changes (confirmed via `git stash`). Fix: store/compare in one timezone (e.g. `datetime('now', 'localtime')`, or convert `created_at` to local before `.date()`) | Bug |
| CSRF protection (whole app) | No form in Spendly has CSRF protection yet. Not urgent for the Step 6 filter (GET forms that change nothing), but the edit-profile POST form would benefit. Raised as "FYI" by `spendly-security-reviewer` in the Step 6 review | Needs its own spec |
| `.claude/specs/03-login-and-logout.md` | §8 Acceptance Criteria still all unchecked `- [ ]` in the spec itself, even though `.claude/plans/03-login-and-logout.md` documents completed manual verification with actual `curl` output — spec and plan are out of sync on completion status | Doc-only |
