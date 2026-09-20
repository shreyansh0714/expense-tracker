# Spec 06b — Profile dashboard restructure

**Status:** Draft — not yet implemented
**Branch:** `feature/profile-dashboard-restructure` (branched off
`feature/analytics-coming-soon`, because FR6 needs the `/analytics` route
that branch adds)
**Date:** 2026-09-20

**Supersedes parts of `06-date-time-filter.md`:**

| Superseded | What 06 said | What 06b says |
|---|---|---|
| FR9, treatment | The monthly budget is a **card** — a bordered block with a title, a large amount, and a `<details>` Edit control | It is a **control on a slim bar**, sharing one row with the range summary |
| FR9, the tip line | "Under the card, always: the tip line *Your current budget is used for every month in a multi-month view.*" | The same sentence moves **inside** the Add/Edit popover, above the form |
| FR12, look | Two bullets: the filter bar is one rounded bordered card; the budget table is a boxed grid with a green header | Both bullets stand. A third is added: the range+budget bar is a second rounded bordered card, visually matched to the filter row above it |

**Not superseded — explicitly reaffirmed:** FR9's *placement* rule already
reads "directly below the filter bar on the **right**. The 'Showing …' line,
pill, notes and filter errors sit on the left of the same row"
(`06-date-time-filter.md:105-106`). The current build renders these two
**backwards** — `profile.html`'s `.filter-summary-row` puts the budget on the
left and the summary on the right. FR3 below is therefore a *bug fix toward
spec 06*, not a change to it. FR10 (the `<span class="range-pill">`) and FR11
(Indian digit grouping, `₹10,000.00`) are unchanged and must keep passing.

---

## 1. Problem Statement

The `/profile` dashboard was built one section at a time across Steps 4, 5 and
6. Each addition was correct on its own, but nothing ever re-read the page as a
whole, and it now has three concrete structural faults:

1. **The budget and the range summary fight for one row, in the wrong order.**
   `.filter-summary-row` renders a 320px-wide budget card on the left and the
   "Showing 1 Sep 2026 – 20 Sep 2026" text on the right — the reverse of what
   spec 06 FR9 specifies. Two blocks of unequal weight sit side by side with no
   clear primary.
2. **The month-by-month budget table interrupts the page.** It renders between
   the stat tiles and the transactions/category grid, splitting the page's main
   content in half with a wide table that only appears on some ranges.
3. **The three stat tiles have no visual anchor.** They are label-over-value
   text in a bordered box, so the page's three most important numbers carry no
   more weight than anything else on it.

Two infographics in `static/images/` define the fix — a single top-to-bottom
flow: header → filter row → one slim range+budget bar → three key stats →
transactions + categories → budget table last.

Alongside the reorder, three gaps close: the page has no icon set (it uses the
bare HTML entity `&#9998;` in two places), all seven expense categories share
only three colors, and an account with no expenses shows the same message
whether it has never logged one or has simply filtered to an empty range.

## 2. Functional Requirements

### FR1 — Block order

`/profile` renders these blocks, top to bottom, in exactly this order:

| # | Block | Condition |
|---|---|---|
| 1 | Profile header card (avatar, name, email, member-since, Edit profile button) with the Notes-to-self sticky attached at its corner | always |
| 2 | Date filter row (`.date-filter`) | always |
| 3 | Range + budget bar (`.range-budget-bar`) | always |
| 4 | Three stat tiles (`.profile-stats-row`) | always |
| 5 | Content grid (`.profile-content-grid`) — Recent Transactions, By Category | always |
| 6 | Month-by-month budget table | only when `monthly_budget_rows` is non-empty |

Blocks 1 and 2 are **unchanged** from their current implementation. Block 6
moves from its current position (between blocks 4 and 5) to last.

### FR2 — The date filter row is unchanged

`.date-filter` already renders as one rounded bordered card holding the four
preset buttons and the custom From/To + Apply controls, separated by a vertical
divider. This satisfies the infographic. **No markup or CSS in that block
changes.**

The From/To boxes stay **blank** unless `active_range == 'custom'`. The
infographic shows them pre-filled with the active month's dates while the
`This month` preset is highlighted; that is mockup realism, not a requirement.
Pre-filling them would make a custom range look active when it is not.

### FR3 — The range + budget bar

One horizontal bar, styled as a second rounded bordered card matched to the
filter row above it.

**Left side:** the range summary — `Showing <start> – <end>` followed by the
`<span class="range-pill">` carrying the active range's label. Both survive
from spec 06 FR10 unchanged.

**Right side, exactly one of:**

| State | Renders |
|---|---|
| `budget_amount is none` | A control reading `Add monthly budget`, preceded by a plus icon |
| `budget_amount` is set | The amount `₹<budget_amount>` formatted per FR11, then a control reading `Edit`, preceded by a pencil icon |

Both controls open the same budget form — a `<details>` element whose body
holds the existing `budget_form()` macro, unchanged, still POSTing to
`url_for('save_budget')` with its hidden `range`/`start`/`end` fields.

The tip line `Your current budget is used for every month in a multi-month
view.` renders **inside** that popover, above the form fields.

**Below the bar, full width when present:** the filter error
(`filter_error`) and the range note (`range_note`). They must not sit inside
the bar — a long note would otherwise squeeze the budget control.

The popover must open **without shifting the blocks below it**.

### FR4 — Stat tiles gain icon badges

Each of the three tiles becomes a two-part row: a text column on the left
holding the existing label, value and optional subtext, and a circular badge on
the right holding an icon.

| Tile | Label | Icon |
|---|---|---|
| 1 | `Total Spent` | wallet (Feather `credit-card`) |
| 2 | `Transactions` | list (Feather `list`) |
| 3 | `Top Category` | heart (Feather `heart`) |

Labels keep the casing spec 05 established — `Total Spent`, not the
infographic's `Total spent`. The `.stat-tile-subtext` budget-used line stays
inside the text column.

### FR5 — Icons come from one reusable macro file

All icons are inline `<svg>` Feather glyphs defined in `templates/_icons.html`,
one macro per glyph, imported once per template. No npm package, no icon font,
no CDN request, no per-use pasted SVG.

Required glyphs: `edit` (pencil), `plus`, `wallet`, `list`, `heart`.

Every icon is decorative and sits beside real text, so each carries
`aria-hidden="true"` and there are **no icon-only controls**. Each uses
`stroke="currentColor"` so it inherits color from its container.

The two existing `&#9998;` entities — on the Edit profile button and the budget
Edit control — are replaced by the `edit` macro. The visible word beside each
(`Edit profile`, `Edit`) is unchanged.

The date inputs need no icon: the calendar glyph in the infographic is Chrome's
own `<input type="date">` picker indicator, already present.

### FR6 — "View all" on the transactions card

The Recent Transactions card's title row gains a right-aligned link reading
`View all`, pointing at `url_for('analytics')`.

### FR7 — One color per category

Each expense category renders in its own color, used for both its bar fill in
the By Category card and its pill tint in the transactions table.

| Category | Token | Hex |
|---|---|---|
| Food | `--cat-food` | `#1a472a` |
| Entertainment | `--cat-entertainment` | `#7a3f6d` |
| Bills | `--cat-bills` | `#a34434` |
| Transport | `--cat-transport` | `#3d6b8e` |
| Health | `--cat-health` | `#4a7d57` |
| Other | `--cat-other` | `#8a8577` |
| Shopping | `--cat-shopping` | `#b8761f` |

Listed in ascending lightness, so no two adjacent entries collapse together
when hue information is lost. `--cat-food` is exactly `--accent`.
`--cat-shopping` is `--accent-2` darkened one step: at its original `#c17f24`
the bar fill measured **2.79:1** against the `--border-soft` track, under the
3:1 WCAG non-text threshold; `#b8761f` measures 3.12:1. No existing token is
redefined — `--accent-2` itself keeps `#c17f24`.

Measured contrast, all seven: pill text over its own tint ranges 4.89:1 to
10.35:1 (all clear AA 4.5:1); bar fill over the track ranges 3.09:1 to 8.91:1
(all clear 3:1).

`expenses.category` is free text with no `CHECK` constraint
(`database/db.py:28-39`), so **an unrecognised category must still render** —
it falls back to `--cat-other`, never to an unstyled element.

Color is redundant encoding throughout: every bar and every pill sits directly
beside its category name in text, so no information depends on telling two
hues apart.

### FR8 — Empty states distinguish two situations

| Situation | Condition | Both cards show |
|---|---|---|
| Never logged an expense | `get_first_expense_date(user_id)` returns `None` | `You haven't logged any expenses yet.` |
| Logged expenses, but none in this range | first-expense date exists, `recent_expenses` / `category_totals` empty | `No expenses between <start> and <end>. Try a wider range.` |

`<start>` and `<end>` are the **effective** range — the same
`range_start_label` / `range_end_label` the bar shows in FR9, after any
spec 06 FR6 history-start adjustment has been applied. They are not the raw
`?start=` / `?end=` query values. Concretely: if you request
`?range=custom&start=2020-01-01&end=2026-09-20` on an account whose records
begin 5 Jul 2026, the bar reads `Showing 5 Jul 2026 – 20 Sep 2026` and the
empty-state message must name those same two dates, so the page never shows
two different ranges at once.

Neither message is a link. `/expenses/add` is a Step 7 stub returning the raw
string `"Add expense — coming in Step 7"`, and CLAUDE.md forbids implementing
it early, so nothing on this page may point at it.

The three stat tiles keep rendering their real values in both situations
(`₹0.00`, `0`, `—`).

### FR9 — The range summary text comes from the route

The template must not build the "1 Sep 2026" date text itself. `app.py`
already has `format_day()`, which produces exactly that string for the range
notes; the route passes `range_start_label` and `range_end_label` built with
it, and the template renders those.

This closes an Open Task already recorded in `.claude/PROGRESS.md`: "The
template builds that date text itself (`range_start.day` + `strftime('%b
%Y')`), while `app.py` already has a helper, `format_day()`, that makes the
exact same '19 Sep 2026' text… Two copies of one format means a future format
change has to be made in both."

### FR10 — The Notes sticky is unchanged

The Notes-to-self sticky stays exactly where it is, attached to the header
card's corner. It appears in neither infographic, but those are structure
diagrams rather than inventories — the before/after one lists six blocks, the
structure one shows four, and neither draws the month-by-month table this spec
explicitly keeps.

It is also load-bearing: it holds `<textarea name="notes" form="profile-form">`,
the only render and edit surface for the persisted `users.notes` column.

### FR11 — Theme last

The paper-ledger treatment (`spendly-ui-polish`) is applied to the new bar and
the restructured tiles **after** the structure and colors are reviewed, as a
separate pass. Per CLAUDE.md's Session scope convention, structure, content and
visual polish must not ship as one uninterrupted implementation.

## 3. APIs

**No route signature, query, or schema changes.**

`GET /profile` keeps its existing query parameters (`range`, `start`, `end`),
its always-200 contract, and all five error strings from spec 06.
`POST /profile/budget` keeps its always-302 contract and its three toasts.

Two additions to the template context that `profile()` already builds:

| Key | Type | Value |
|---|---|---|
| `range_start_label` | `str` | `format_day(range_start)`, e.g. `"1 Sep 2026"` |
| `range_end_label` | `str` | `format_day(range_end)`, e.g. `"20 Sep 2026"` |
| `has_expenses` | `bool` | `first_expense_date is not None` — FR8's discriminator |

`first_expense_date` is already computed in `profile()` for the history-start
calculation; `has_expenses` reuses it and costs no extra query.

## 4. Files and Interfaces Involved

| File | Change |
|---|---|
| `templates/_icons.html` | **New.** Five Feather glyph macros (FR5) |
| `templates/profile.html` | Import the macros; replace `.filter-summary-row` with `.range-budget-bar` (FR3); restructure the three stat tiles (FR4); add the View all link (FR6); move the budget-table block after the content grid (FR1); branch the two empty states (FR8); render the label variables (FR9) |
| `static/css/profile.css` | Delete `.filter-summary-row`, `.filter-summary`, `.budget-card-wrap`, `.tilt-h`, the `.budget-card*` block and the dead half of the `max-width: 800px` block. Add a `/* --- Range + budget bar --- */` section. Keep every `.budget-form*` / `.budget-input-*` / `.budget-save-btn` rule |
| `static/css/style.css` | Seven `--cat-*` tokens in `:root` (FR7); rewrite the `[data-category]` rules on `.category-bar-fill` and `.category-pill`; `.stat-tile` becomes a row, plus `.stat-tile-text` and `.stat-tile-icon` (FR4); `.card-header` / `.card-header-link` (FR6) |
| `app.py` | In `profile()`'s `dashboard` dict only: `range_start_label`, `range_end_label`, `has_expenses`. No other change |
| `.claude/PROGRESS.md` | Record Step 6b; flip the duplicate-date-format Open Task to Resolved |

**Interfaces that must not change:** `resolve_date_range()`,
`build_budget_rows()`, `format_day()`, `format_inr()`, every `database/db.py`
helper, and the `save_budget()` route.

**DOM hooks `static/js/main.js` binds — all must survive:**
`#open-edit-profile` (IIFE 3), `#profile-form` and `#email` (IIFE 4),
`.date-filter-custom input[type="date"]` (IIFE 5). The icon goes *inside* the
existing `<button id="open-edit-profile">`; the button element itself is
untouched.

## 5. Constraints

- Flask + Jinja2 + raw `sqlite3`. No npm, no build step, no new pip package, no
  ORM, no blueprints, no app factory.
- Routes stay in `app.py`; data access stays in `database/db.py`.
- Templates extend `base.html`. Page-specific CSS goes in `profile.css`; shared
  rules and all `:root` tokens go in `style.css`. No inline `<style>`.
- Every color, radius and font goes through a CSS custom property. `--accent`,
  `--accent-2` and `--danger` keep their current values.
- The budget popover is pure CSS on a native `<details>` — spec 06 FR9's "needs
  no JavaScript" still holds.
- `color-mix()` is permitted for deriving pill tints from the seven tokens. It
  is Baseline 2023; the project has no build step or autoprefixer, and where
  unsupported the declaration is dropped and the pill falls back to its base
  rule rather than breaking.
- All 45 tests in `tests/test_06-date-time-filter.py` must pass on completion
  (`venv/bin/python -m pytest --collect-only -q` reports 45 collected today).

## 6. Out of Scope

- Any change to `database/db.py`, the schema, or any SQL query.
- Implementing `/expenses/add`, `/expenses/<id>/edit` or `/expenses/<id>/delete`
  (Steps 7, 8, 9).
- Real analytics content on `/analytics` — it stays the coming-soon page.
- Any at-a-glance trend, sparkline, or month-over-month comparison on
  `/profile`. The page stops where the infographics stop; richer analysis waits
  for the Analytics feature and its own spec.
- Renaming `format_day()` to `format_short_date`, and splitting
  `resolve_date_range()` — both are separate optional cleanups in PROGRESS.md.
- CSRF protection, which PROGRESS.md tracks as needing its own spec.
- Paginating the transactions table beyond its current 5-row cap.

## 7. Edge Cases and Error Handling

| # | Case | Expected |
|---|---|---|
| E1 | Unknown category string, e.g. `Dining out` | Bar and pill render in `--cat-other`. No unstyled element, no layout break |
| E2 | Category differing only by case, e.g. `FOOD` | `data-category="{{ …\|lower }}"` already normalises it; renders as Food |
| E3 | Brand-new account, no expenses ever | FR8 row 1 message in both cards; tiles show `₹0.00`, `0`, `—`; bar shows `Add monthly budget` |
| E4 | Expenses exist, filter matches none | FR8 row 2 message naming both range ends |
| E5 | `filter_error` and `range_note` both present | Both render full-width below the bar, stacked, in that order |
| E6 | A very long range note | Wraps below the bar. The budget control's width is unaffected |
| E7 | Budget popover open, then the page is filtered | The `<details>` closes on navigation; the hidden `range`/`start`/`end` fields preserve the filter across the POST redirect |
| E8 | Budget ≥ ₹10,00,000 | Renders with Indian digit grouping per FR11 — never scientific notation |
| E9 | Single-month range with a budget | No month-by-month table; the `.stat-tile-subtext` budget-used line shows on tile 1 |
| E10 | Multi-month range, no budget set | No month-by-month table (nothing to compare against); bar shows `Add monthly budget` |
| E11 | Viewport at 375px | Bar stacks to two rows; popover goes full-width inline instead of floating; tiles stack one per row with the badge still right-aligned; no horizontal page scroll |
| E12 | `prefers-reduced-motion: reduce` | The sticky's expand transition and the modal's crumple animation stay disabled |

## 8. Acceptance Criteria

- [ ] **AC1** — Blocks render in FR1's order; the month-by-month table appears
      below the content grid, not above it
- [ ] **AC2** — `.date-filter` markup and CSS are byte-identical to before
- [ ] **AC3** — From/To boxes are empty unless `active_range == 'custom'`
- [ ] **AC4** — The bar shows `Showing <start> – <end>` plus the range pill on
      the left
- [ ] **AC5** — With no budget, the bar's right side reads `Add monthly budget`
      with a plus icon
- [ ] **AC6** — With a budget, it reads the amount plus an `Edit` control with a
      pencil icon; `Add monthly budget` is absent
- [ ] **AC7** — Opening the popover does not move the stat tiles below it
- [ ] **AC8** — The tip line appears inside the popover, not on the bar
- [ ] **AC9** — `filter_error` and `range_note` render full-width below the bar
- [ ] **AC10** — Each stat tile shows label + value on the left and a circular
      icon badge on the right; labels read `Total Spent`, `Transactions`,
      `Top Category`
- [ ] **AC11** — `templates/_icons.html` exists with five macros; no `&#9998;`
      entity remains in `profile.html`; no icon-only control exists
- [ ] **AC12** — The Recent Transactions card shows a `View all` link whose
      `href` is `/analytics`
- [ ] **AC13** — Seven `--cat-*` tokens exist in `:root` with FR7's values;
      `--accent`, `--accent-2`, `--danger` are unchanged
- [ ] **AC14** — Seven categories render seven distinct bar colors and seven
      distinct pill tints
- [ ] **AC15** — An unrecognised category renders in `--cat-other`
- [ ] **AC16** — A never-used account shows `You haven't logged any expenses
      yet.` in both cards
- [ ] **AC17** — An account with expenses but an empty range shows `No expenses
      between <start> and <end>. Try a wider range.`
- [ ] **AC18** — `profile.html` contains no `strftime` call; the route supplies
      `range_start_label` / `range_end_label`
- [ ] **AC19** — The Notes sticky still renders, still saves, still expands on
      focus
- [ ] **AC20** — Edit profile opens; the email-change verification popup still
      triggers; the date picker still opens on click
- [ ] **AC21** — At 375px nothing overflows horizontally
- [ ] **AC22** — `venv/bin/python -m pytest` is fully green

## 9. Manual Verification Guide

Assume no prior familiarity with any tool named here. Run every step in order.

### Setup (do this once)

1. Open Terminal and go to the project:
   `cd "/Users/shreyanshjain/Desktop/Expense Tracker/expense-tracker"`
2. Start the server: `venv/bin/python app.py`
   Expected: a line containing `Running on http://127.0.0.1:5001`.
   **Leave this window open.** Open a second Terminal window for commands.
3. In Chrome, go to `http://localhost:5001/login`, sign in as
   `demo@spendly.com` with password `demo123`.
   Expected: you land on `/profile`.

### AC1 — Block order

4. On `/profile`, scroll top to bottom and write down what you see, in order.
   Expected, exactly: your name card → the row of `This month / Last month /
   Last 3 months / All time` buttons → a thin bar with `Showing …` → three
   boxes (`Total Spent`, `Transactions`, `Top Category`) → two side-by-side
   cards (`Recent Transactions`, `By Category`).
5. Change the URL to `http://localhost:5001/profile?range=last_3_months` and
   press Enter. A `Month-by-month budget` table now appears.
   Expected: it is **below** the two side-by-side cards. If it sits above
   them, AC1 fails.

### AC2, AC3 — The filter row is untouched

6. In the second Terminal:
   `git diff main -- static/css/profile.css | grep -c "date-filter"`
   Expected output: `0`. Any other number means the filter CSS was touched.
7. Back on `/profile?range=this_month`, look at the `From` and `To` boxes.
   Expected: both empty, showing only `dd/mm/yyyy`.
8. Pick any date in `From`, any later date in `To`, click `Apply`.
   Expected: both boxes now show the dates you picked.

### AC4–AC9 — The range + budget bar

9. Look at the thin bar under the filter row.
   Expected on the left: `Showing 1 Sep 2026 – 20 Sep 2026` (your dates will
   differ), then a small dark-green rounded pill reading `This month`.
10. Remove any existing budget so you can see the empty state. In Terminal:
    `sqlite3 database.db "UPDATE users SET monthly_budget = NULL WHERE email = 'demo@spendly.com';"`
    Then reload `/profile`.
    Expected on the bar's right: a `+`-style icon then the words
    `Add monthly budget`. **AC5.**
11. Before clicking, note where the `Total Spent` box sits on screen — pick a
    landmark, e.g. how far below the bar its top edge is.
12. Click `Add monthly budget`.
    Expected: a small panel opens showing the sentence `Your current budget is
    used for every month in a multi-month view.` above a `₹` input and a
    `Save budget` button. **AC8.**
    Expected: the `Total Spent` box has **not** moved down. **AC7.**
13. Type `10,000` and click `Save budget`.
    Expected: a toast reading `Budget saved.`, and the bar now shows
    `₹10,000.00` followed by a pencil icon and the word `Edit`, with
    `Add monthly budget` gone. **AC6.**
14. Go to `http://localhost:5001/profile?range=custom&start=&end=`
    Expected: the text `Please choose both a start and an end date.` appears on
    its own line **below** the bar, spanning the full page width — not squeezed
    inside the bar next to the budget. **AC9.**

### AC10, AC11 — Stat tiles and icons

15. Look at the three boxes under the bar.
    Expected in each: the label and the number on the left, and on the right a
    pale-green circle containing a small dark-green line-drawn icon — a card
    shape, a list, and a heart, in that order. **AC10.**
16. Confirm the labels read exactly `Total Spent`, `Transactions`,
    `Top Category` — capital S, capital C.
17. In Terminal: `grep -c "9998" templates/profile.html`
    Expected output: `0`. **AC11.**
18. `ls templates/_icons.html` → expected: the path prints back, no error.
19. Check the five icons actually render, rather than counting lines in the
    source (the SVG envelope is shared by a helper macro, so it is written
    once, not five times):
    ```
    venv/bin/python -c "
    from app import app
    from flask import render_template_string
    with app.app_context():
        o = render_template_string(\"{% import '_icons.html' as i %}{{ i.edit() }}{{ i.plus() }}{{ i.wallet() }}{{ i.list() }}{{ i.heart() }}\")
    print('svgs:', o.count('<svg'), 'aria-hidden:', o.count('aria-hidden'))
    "
    ```
    Expected output: `svgs: 5 aria-hidden: 5`.

### AC12 — View all

20. Find the `View all` link at the top-right of the `Recent Transactions`
    card. Hover it and read the URL Chrome shows in the bottom-left corner.
    Expected: it ends in `/analytics`.
21. Click it. Expected: the Analytics coming-soon page loads.
22. Press the browser Back button to return to `/profile`.

### AC13–AC15 — Category colors

23. In Terminal:
    `grep -c "^    --cat-" static/css/style.css` → expected: `7`.
24. `grep -E "^\s+--accent:|^\s+--accent-2:|^\s+--danger:" static/css/style.css`
    Expected exactly:
    `--accent: #1a472a;`, `--accent-2: #c17f24;`, `--danger: #c0392b;`
    **AC13.**
25. Seed one expense in every category so all seven bars appear. Run
    `/seed-expense` and follow its prompts, or in Terminal:
    ```
    sqlite3 database.db "INSERT INTO expenses (user_id, amount, category, date, description) SELECT id, 100, 'Dining out', date('now'), '[06b-test] unknown category' FROM users WHERE email='demo@spendly.com';"
    ```
26. Reload `/profile`. Look at the `By Category` card.
    Expected: each category's bar is a visibly different color from every other
    one. **AC14.**
    Expected: the `Dining out` row renders in a muted warm grey, and its row is
    laid out identically to the others. **AC15.**
27. **Clean up the row you just created** — this is real data in your database:
    ```
    sqlite3 database.db "DELETE FROM expenses WHERE description LIKE '[06b-test]%';"
    ```
    Then verify it is gone:
    `sqlite3 database.db "SELECT COUNT(*) FROM expenses WHERE description LIKE '[06b-test]%';"`
    Expected output: `0`.

### AC16, AC17 — Empty states

28. Make a throwaway account: go to `http://localhost:5001/register`, sign up
    with `empty@test.com` / `testpass1`.
    Expected: you land on `/profile` with no expenses.
29. Expected in both the `Recent Transactions` and `By Category` cards:
    `You haven't logged any expenses yet.` **AC16.**
30. Sign out, sign back in as `demo@spendly.com`, then go to
    `http://localhost:5001/profile?range=custom&start=2020-01-01&end=2020-01-03`
    Expected in both cards: `No expenses between 1 Jan 2020 and 3 Jan 2020.
    Try a wider range.` **AC17.**
31. **Clean up the throwaway account:**
    `sqlite3 database.db "DELETE FROM users WHERE email = 'empty@test.com';"`

### AC18 — Date text comes from the route

32. `grep -c "strftime" templates/profile.html`
    Expected output: `0`. Any other number means the template still formats
    dates itself.

### AC19, AC20 — Nothing existing broke

33. On `/profile`, find the yellow taped note at the top-right of your name
    card. Click into it — it should grow larger. Type `verification test`.
34. Click `Edit profile`, then `Save changes` in the popup.
    Expected: a toast `Profile updated.`
35. Reload the page. Expected: `verification test` is still in the note.
    **AC19.**
36. Click `Edit profile` again, change the email to `changed@test.com`, click
    `Save changes`.
    Expected: a second popup appears asking for a verification code. Close it
    with the `×` and do **not** save. **AC20.**
37. Click anywhere inside the `From` box.
    Expected: the date picker opens immediately. **AC20.**

### AC21 — Mobile

38. Press `Cmd+Option+I` to open DevTools, then `Cmd+Shift+M` for device mode.
    In the dropdown at the top, choose `iPhone SE` (375px wide).
39. Scroll the whole page.
    Expected: the bar has stacked into two rows; the three tiles are one per
    row, each still with its icon on the right; the two content cards are
    stacked; and there is **no** horizontal scrollbar at the bottom.

### AC22 — Tests

40. Stop the server in the first window with `Ctrl+C`, then run:
    `venv/bin/python -m pytest`
    Expected last line: `45 passed`, and **no** `failed` or `error`.

## 10. End-to-End Verification

One command proving the restructure holds together, run from the project root
with the server stopped:

```bash
venv/bin/python - <<'PY'
from app import app
app.config["SECRET_KEY"] = "test"
c = app.test_client()
with c.session_transaction() as s:
    s["user_id"] = 1

html = c.get("/profile?range=last_3_months").data.decode()

# FR1: the budget table renders after the content grid
grid  = html.index('class="profile-content-grid"')
table = html.index('budget-table')
assert grid < table, "FR1: month-by-month table must come after the content grid"

# FR3/FR6/FR9: the bar, the link, and route-supplied date labels
assert 'range-budget-bar' in html
assert 'href="/analytics"' in html, "FR6: View all must point at /analytics"
assert 'range-pill' in html, "spec 06 FR10 still applies"

# FR5: no bare pencil entity survives, and icons are decorative
assert '&#9998;' not in html and '✎' not in html, "FR5: entity must be gone"

print("end-to-end OK")
PY
```

Expected output: `end-to-end OK`, with no `AssertionError`.

This reads only — it opens no write transaction and creates no rows, so
nothing needs cleaning up afterwards.
