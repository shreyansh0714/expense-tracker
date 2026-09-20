# Plan 06b — Profile dashboard restructure

Pairs with `.claude/specs/06b-profile-dashboard-restructure.md`.
Branch: `feature/profile-dashboard-restructure`, branched off
`feature/analytics-coming-soon` (FR6 needs the `/analytics` route that
branch adds; `main` doesn't have it yet).

## Context / Scope

The `/profile` dashboard grew a section at a time across Steps 4, 5 and 6 and
was never re-read as a whole. Two infographics added to `static/images/` on
2026-09-20 define the fix as one top-to-bottom flow. The spec's Problem
Statement names the three concrete faults; this plan is how they get fixed.

**Everything here is `templates/` + `static/css/`, plus three lines in
`app.py`.** No route signature, no query, no schema change — `profile()`
already passes every value the new layout needs.

## Design Plan

### Block order (spec FR1)

| # | Block | Change |
|---|---|---|
| 1 | Header card + Notes sticky | none |
| 2 | `.date-filter` | none — already one row with a divider, matches the infographic |
| 3 | `.range-budget-bar` | **new**, replaces `.filter-summary-row` |
| 4 | `.profile-stats-row` | restructured to text + icon badge |
| 5 | `.profile-content-grid` | gains the View all link |
| 6 | Month-by-month budget table | **moved** from between 4 and 5 to last |

### The bar (FR3)

Today `.filter-summary-row` is a flex row with a 320px `.budget-card-wrap` on
the left and `.filter-summary` on the right. Spec 06 FR9 asked for the
opposite order, so this is a fix, not a reinvention. The new bar is one flex
row, `justify-content: space-between`, reusing the `--paper-card` /
`--border` / `--radius-lg` treatment `.date-filter` already carries, so the
two bars read as a pair.

The budget `<details>` becomes a popover: `position: absolute; right: 0;
top: calc(100% + .4rem)` on a `position: relative` parent, so opening it
doesn't push the stat tiles down (AC7). Under 800px it goes `position: static;
width: 100%` so it can't overflow a narrow viewport. Pure CSS — spec 06 FR9's
"needs no JavaScript" still holds.

`filter_error` and `range_note` move **out** of the bar to full-width rows
below it, so a long note can't squeeze the budget control.

### Icons (FR5)

`templates/_icons.html`, one macro per glyph rather than a single
`icon(name)` dispatcher: a typo in `icons.wallett()` raises a Jinja
`UndefinedError` immediately, where an `{% if name == … %}` chain would
silently render nothing.

Each macro emits the standard Feather envelope — `viewBox="0 0 24 24"
fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
stroke-linejoin="round" aria-hidden="true"` — with size as a macro argument.
`stroke="currentColor"` is the load-bearing part: zero per-icon colour CSS,
each glyph inherits its container's `color`.

### Category colours (FR7)

Seven `--cat-*` tokens on a lightness ladder (L\* ≈ 26 → 37 → 42 → 43 → 47 →
56 → 58) so no two adjacent entries collapse together when hue information is
lost. `--cat-food` and `--cat-shopping` reuse the existing `--accent` /
`--accent-2` values rather than adding near-duplicates.

The existing unattributed base rules (`.category-bar-fill` at style.css:930,
`.category-pill` at :885) stay as the fallback, repointed at `--cat-other` —
that is what already solves the free-text category case, so it needs keeping,
not replacing.

Pill tints derive natively: `color-mix(in srgb, var(--cat-x) 14%,
var(--paper-card))` for the background, `color-mix(in srgb, var(--cat-x) 70%,
var(--ink))` for the text. Darkening the text toward ink guarantees contrast
on the pale tint for all seven without seven more tokens. Where `color-mix`
isn't supported the declaration is dropped and the pill falls back to its base
rule.

### What must not break

`static/js/main.js` binds `#open-edit-profile` (IIFE 3), `#profile-form` and
`#email` (IIFE 4), and `.date-filter-custom input[type="date"]` (IIFE 5). The
icon goes *inside* the existing `<button id="open-edit-profile">`; the button
element itself is untouched. Block 2 isn't touched at all.

## Tasks

### Pass 1 — Spec (done)

- [x] `/create-spec profile-dashboard-restructure 06b` — branch + spec written
- [x] Confirm the suite size (`pytest --collect-only -q` → 45, not 37)
- [x] Copy this plan into the repo as `.claude/plans/06b-…md`

### Pass 2 — Structure (no colours, no theme)

- [x] `templates/_icons.html` — five macros: `edit`, `plus`, `wallet`, `list`, `heart`
- [x] `app.py` — add `range_start_label`, `range_end_label`, `has_expenses` to `profile()`'s `dashboard` dict
- [x] `templates/profile.html` — import the macros; swap both `&#9998;` entities
- [x] `templates/profile.html` — replace `.filter-summary-row` with `.range-budget-bar`; move the tip line into the popover
- [x] `templates/profile.html` — restructure the three stat tiles into text + badge
- [x] `templates/profile.html` — add the View all link
- [x] `templates/profile.html` — move the budget-table block after the content grid
- [x] `templates/profile.html` — branch the two empty states (FR8)
- [x] `static/css/profile.css` — add the bar + popover section; delete the dead `.filter-summary-row` / `.budget-card-wrap` / `.budget-card*` rules and the dead half of the 800px media block
- [x] Browser check at 1280px and 375px → **stop for review**

### Pass 3 — Colour

- [x] `static/css/style.css` — seven `--cat-*` tokens in `:root`
- [x] `static/css/style.css` — rewrite the `[data-category]` rules for `.category-bar-fill` and `.category-pill`; repoint the base rules at `--cat-other`
- [x] `static/css/style.css` — `.stat-tile` row layout, `.stat-tile-text`, `.stat-tile-icon`, `.card-header`, `.card-header-link`
- [x] Seed one unknown category, confirm the fallback, delete the seeded row → **stop for review**

### Pass 4 — Theme

- [x] `spendly-ui-polish` pass — the bar keeps the filter row's crisp border per FR3 ("matched to the filter row"), so no hand-drawn border or tilt on it; typography left on `--font-display` to match the existing `.stat-tile-value`
- [x] **Folded in:** fixed the hand-drawn card borders, which rendered on no card but the page header. Cause was paint order — `.hand-drawn > svg` sat *behind* the card's opaque `--paper-card` background. Fix: `z-index: 2` + `overflow: visible` on the svg, `pointer-events` already off
- [x] Re-check `prefers-reduced-motion` — sticky transition computes to `0s` under `reduce`
- [x] Confirm JS hooks survive: modal opens, `notes` textarea still targets `#profile-form`, 2 date inputs bound, `#email` keeps `data-original-email`

### Pass 5 — Checks and close-out

- [x] `venv/bin/python -m pytest` — **51 green** (the regenerated Step 6 file collects 51, not the old 45)
- [x] `/test-feature 06-date-time-filter` — regenerated from the marked spec. Round 1: 47 pass / 4 fail, all four traced to test-code defects (case-sensitive `method="get"`, a second user registered through the authenticated client hijacking its own session, a dropped `html.unescape` helper, and a page-wide substring search colliding with `Member since Sep 2026`). Sent back, fixed, round 2 green
- [x] `/test-feature 06b-profile-dashboard-restructure` — new `tests/test_06b-profile-dashboard-restructure.py`, 19 tests. Round 1: 15/17 pass; the 2 failures counted `\bEdit\b` page-wide and collided with the edit-profile modal's own `<h2>Edit profile</h2>`. Fixed by scoping to a `bar_slice()` helper rather than bumping the expected number. AC3 coverage added (it was missing from my brief, not the writer's output)
- [x] Mutation-checked the block-order assertion: moving the budget table back above the content grid fails `TestBlockOrder` and nothing else
- [x] Full suite: **70 passed** (51 Step 6 + 19 Step 6b)
- [x] `/code-review-feature 06b-profile-dashboard-restructure` — security: **no findings** (XSS conclusion additionally verified by firing 3 real payloads at a throwaway DB; all escaped). Quality: **CHANGES REQUESTED** on one line, `static/css/analytics.css:42` hardcoded `rgba(26, 71, 42, .22)` = `--accent`'s exact value. Fixed with `color-mix(in srgb, var(--accent) 22%, transparent)`
- [x] Deferred the one non-blocking suggestion (duplicated empty-state block → Jinja macro) to PROGRESS.md Open Tasks
- [ ] Developer runs the spec's Manual Verification Guide
- [x] `.claude/PROGRESS.md` — Step 6b section added, route rows updated, duplicate-date-format Open Task → Resolved, browser-verification Open Task → Partly resolved
- [x] Closed `SPEC GAP: 4` in spec 06b FR8 — `<start>`/`<end>` are the effective range after history-start adjustment, not the raw query values
- [ ] Commit, push, PR, merge (analytics branch merges first — this one is stacked on it)

## Verification

Tied to the spec's §10 End-to-End Verification, which asserts block order
(`profile-content-grid` index < `budget-table` index), the bar's presence, the
`/analytics` href, the surviving `range-pill`, and that no `&#9998;` entity
remains. It is read-only — no rows created, nothing to clean up.

Plus, after Pass 4: `venv/bin/python -m pytest` must report 45 passed.

The spec's §9 Manual Verification Guide covers everything a browser has to
show — it is the developer's pass, not mine, per CLAUDE.md's rule that the
main agent never self-verifies a feature.

## Explicitly out of scope

- Any `database/db.py`, schema or SQL change
- Implementing the Step 7/8/9 expense stubs
- Real analytics content on `/analytics`
- Trends, sparklines or month-over-month comparison on `/profile`
- Renaming `format_day()`, splitting `resolve_date_range()`, CSRF — all
  separate PROGRESS.md entries
