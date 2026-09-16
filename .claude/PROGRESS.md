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
- [x] Pushed to `origin/feature/profile-page`; PR opened, **not yet merged
      to `main`**
- [ ] Fix the concrete issues found in the 2026-09-16 subagent audit —
      see **Open Tasks** below. Audit's bottom line: the implementation is
      largely faithful to the spec/plan (layout, content, and styling all
      verified correct); the "missing lots of things" impression traces to
      a small number of specific bugs below, not a broad implementation
      failure — worth double-checking you weren't looking at a stale page
      load or your own account's data instead of the demo account.

## Future Features

Deferred because they need infrastructure this project doesn't have yet,
or their own spec. Not stubs in `app.py` — tracked here so they aren't
lost. Move an entry out once it becomes a real numbered spec under
`.claude/specs/`.

| Feature | Why deferred | Needs |
|---|---|---|
| Playwright end-to-end tests + CI/CD pipeline | Explicitly future work per the developer (2026-09-17) — the project only has Gate 1 (manual + `/code-review`) and Gate 2 (`pytest`) so far | Its own spec — which flows/pages get e2e coverage, and what CI provider/pipeline to use |
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
| Profile page (`templates/profile.html`) | Recent-activity card has a pin decoration not called for by `design-system.md`'s component table (that entry only specifies torn-both + typewriter font + tabular-nums) | Doc/treatment mismatch |
| Profile page (`static/css/style.css`) | `--sticky` / `--sticky-mint` tokens from `design-system.md` were never added to `:root` — harmless today since no page uses the sticky-note treatment yet | Incomplete token set |
| Profile page (`static/css/style.css`) | `.profile-card-title` applies italic to *every* card title, but `design-system.md`'s table only specifies italic for the reference/notes card specifically — may be an intentional broader reading of the Typography section, needs a judgment call | Needs a decision |
| `spendly-ui-polish` skill | The 3 saved eval prompts (`evals/evals.json`) have never actually been run — no results/workspace exist | Unverified |
| `verify` subagent | Referenced as a TODO in 3 places (`CLAUDE.md` Subagent policy, `create-spec.md`, `implement-plan.md`) — still doesn't exist anywhere; whenever it's built, all 3 mentions need updating together, not just one | Known limitation |
| `.claude/skill-briefs/spendly-ui-polish.md` | Stale scaffolding from before `skill-creator` ran — fully superseded by `.claude/skills/spendly-ui-polish/`, drifted out of sync with it. Safe-to-delete candidate | Cleanup |
| `.claude/specs/01-databse-setup.md` | §14 "Definition of Done" checklist still all unchecked `- [ ]`, never flipped after the work was done | Doc-only |
| `.claude/plans/01-database-setup.md` | Describes a verification script to run, but no pass/fail results were ever recorded | Doc-only |
| Step 2 (Registration) | No `.claude/plans/02-registration.md` exists at all — the only Step missing a plan file, breaking `create-spec.md`'s own plan-pairing convention | Missing doc |
| `.claude/specs/03-login-and-logout.md` | §8 Acceptance Criteria still all unchecked `- [ ]` in the spec itself, even though `.claude/plans/03-login-and-logout.md` documents completed manual verification with actual `curl` output — spec and plan are out of sync on completion status | Doc-only |
