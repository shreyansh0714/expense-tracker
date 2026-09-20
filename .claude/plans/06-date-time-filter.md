# Plan 06 — Date Filter on the Profile Dashboard

Spec: `.claude/specs/06-date-time-filter.md`

> **Standing rule for whoever implements this plan:** immediately after finishing each
> task below, re-open this file and check its box. Don't batch checkbox updates to the
> end of a session, and don't rely on memory to know what's done.

Decisions settled while planning (2026-09-19), already written into the spec:

| Question | Decision |
|---|---|
| ₹ format | Keep the page's existing `"%.2f"` (`₹10000.00`, no comma). The spec's AC13 example was corrected to match |
| Where new CSS goes | New `static/css/profile.css`, linked from `profile.html` via `{% block head %}`. Existing profile styles stay in `style.css` |
| Budget table position | Directly below the stat tiles row |
| When the "records begin" notes show | Custom ranges only. Presets never show a note |

## Design Plan

### 1. `database/db.py` — range-aware helpers

- Replace `get_monthly_category_totals(user_id)` → `get_category_totals(user_id, start, end)`
  and `get_monthly_transaction_count(user_id)` → `get_transaction_count(user_id, start, end)`.
  The SQL stays the same except for `date >= ? AND date <= ?` (both ends inclusive, ISO
  strings). This removes the month-range code that is currently copied in both helpers.
  They are renamed because they are no longer "monthly". `/profile` is the only caller
  (checked by exploration).
- `get_recent_expenses(user_id, start, end, limit=5)` adds the same `date` bound.
  `start`/`end` are required, not optional, because the only caller always has a range,
  so a "no bound" SQL branch would never be used.
- New `get_first_expense_date(user_id)` → `SELECT MIN(date) …`, returning an ISO string or `None`.
- New `get_monthly_spend(user_id, start, end)` → `SELECT substr(date, 1, 7) AS month, SUM(amount) AS total … GROUP BY month`.
  The budget table needs this.
- Remove `timedelta` from the imports if nothing uses it any more. `date` is still used by `seed_db`.

### 2. `app.py` — range resolving

- A plain function `resolve_date_range(args, history_start, today)`, placed above the
  routes. It does no DB or Flask access, so tests can call it with fixed dates.
  It returns `(active_range, start, end, note, error)`:
  1. Read `range`. If it is missing or empty, use `this_month`. If it is not one of the
     5 keys, record `Unknown date range.` and fall back to `this_month`.
  2. For a preset, compute start/end from the spec's FR3 table.
     - Last month: `first_of_this_month - timedelta(days=1)` gives the end, then `.replace(day=1)` gives the start.
     - Last 3 months: step the month back twice with year wrap, doing the arithmetic on `year*12 + month`.
  3. For `custom`, validate in this order: both present → both parse with
     `date.fromisoformat` → `start <= end` → `start <= today`. The first failure sets
     its exact spec message and falls back to This month. `fromisoformat` rejects
     `2026-02-30`, `abc` and `19/09/2026`, which is what the spec wants.
  4. Apply the adjustments:
     - Any range: if `end > today`, set `end = today`.
     - Custom range entirely before history start: note (b), dates unchanged.
     - Start before history start: set `start = history_start`. Custom ranges also get note (a).
- `history_start = min(created_at date, first expense date)`. This is computed in the
  route from `get_user_by_id` and `get_first_expense_date`.
- Case (b) needs no special query logic. History start is at or before the oldest
  expense, so a range entirely before it already returns nothing.
- **Why a helper rather than inline code:** it's roughly 40 lines of branching, and the
  route is already about 130 lines long.

### 3. `app.py` — `profile()` wiring

- Today the stats are built once, before the GET/POST split, and passed through three
  separate `render_template` calls (the GET, the validation-error POST and the
  IntegrityError POST).
  - Collect every dashboard value into one `dashboard = {...}` dict and pass `**dashboard`
    in all three calls.
  - Every new variable then goes in one place instead of three, which removes the risk
    of forgetting one.
- The range comes from `request.args`. A POST to `/profile` has no query string, so it
  resolves to This month automatically, which is the spec's FR8 behaviour, with no
  extra code.
- Variables added to the template context:
  - `active_range`, `range_start`, `range_end`, `range_note`, `filter_error`
  - `monthly_budget_rows`
  - `show_budget_subtext`: the single-month check. This keeps that logic out of the template.
- `monthly_budget_rows` is built in the route. The steps:
  1. Walk the calendar months from `range_start` to `range_end`.
  2. For each month, look up its spend in the `get_monthly_spend` results. A missing
     month counts as 0.
  3. Compute `percent = round(spent / budget * 100)`. When the budget is 0, use `None`,
     and the template shows `—`.
  4. The list stays empty when there is no budget, or the range is a single month.

### 4. `templates/profile.html`

- `{% block head %}` links `url_for('static', filename='css/profile.css')`.
- There are two GET forms (spec FR1). They are separate so that pressing Enter in a date
  box doesn't submit the first preset button.
  - **Presets form:** 4 `<button type="submit" name="range" value="…">`. Each gets
    `aria-pressed="true"` when its key matches `active_range`, and `"false"` otherwise.
  - **Custom form:** `<input type="hidden" name="range" value="custom">`, a
    `<input type="date" name="start">` and a `<input type="date" name="end">` (both with
    `max` = today's ISO date), and an Apply button. The date boxes are pre-filled from
    `range_start`/`range_end` when `active_range == 'custom'`.
- Below the forms, in order:
  1. The `filter_error`, reusing the existing `auth-error profile-error` classes
  2. The `range_note`
  3. The `Showing … – …` line, dates formatted `%d %b %Y`
- The Total Spent subtext condition changes from `budget_amount is not none` to `show_budget_subtext`.
- The budget table goes directly under `.profile-stats-row` when `monthly_budget_rows` is
  non-empty. It reuses the `.transactions-table` class for the look and carries the spec's
  caption text.
- Both empty states change to `No expenses in this period.`
- The filter never goes anywhere else. `base.html` is not touched (spec AC18).

### 5. `static/css/profile.css` (new)

- Styles only the new pieces: `.date-filter` bar layout, `.date-filter-preset` plus its
  `[aria-pressed="true"]` active state, the date boxes (reusing `.form-input` from
  `style.css`), `.range-summary`/`.range-note` text, and `.budget-table` spacing.
- Tokens from `:root` only, with a `/* --- Section --- */` banner comment.
- It stays deliberately plain here. Visual polish is its own final task, per the
  session-scope rule.

### Reused from existing code
- `get_db()` connection pattern and try/finally close, from `db.py`.
- `.transactions-table`, `.form-input`, `.auth-error profile-error` and `.profile-empty-state` classes.
- The `"%.2f"|format` money format.
- The `auth_client` fixture, used by tests via `/test-feature`.

## Tasks

Review stops (from CLAUDE.md's session-scope rule): after tasks 5, 7 and 9, stop and
show the developer what's built before continuing.

- [x] 1. `db.py`: rename the two monthly helpers to `get_category_totals` / `get_transaction_count` with `start, end`, add the bound to `get_recent_expenses`, and add `get_first_expense_date` and `get_monthly_spend`. Clean up the imports
- [x] 2. `app.py`: update the `database.db` imports and add the `resolve_date_range(args, history_start, today)` helper (presets only for now: `this_month`, `last_month`, `last_3_months`, `all_time`, unknown key → fallback + `Unknown date range.`)
- [x] 3. `app.py`: refactor `profile()` into a single `dashboard` dict passed as `**dashboard` to all 3 `render_template` calls, computing the stats from the resolved range
- [x] 4. `profile.html`: presets form + custom form (markup only), the "Showing …" line, the new empty-state text. `profile.css` created and linked with basic layout
- [x] 5. Quick smoke check (`python app.py`, open `/profile`, click each preset) → **STOP: show the developer (piece 1: filter + filtered tiles/list/bars)**
- [x] 6. `resolve_date_range`: custom-range validation (the 4 error messages in spec order), future-end trimming, history-start clamping, notes (a)/(b) for custom only. Render `filter_error` and `range_note` in the template
- [x] 7. **STOP: show the developer (piece 2: edge-case notes/errors)**
- [x] 8. Route: `show_budget_subtext` + `monthly_budget_rows`. Template: subtext condition + budget table below the stat tiles, with caption, `—` for a 0 budget
- [x] 9. **STOP: show the developer (piece 3: budget table)**
- [x] 10. `profile.css` visual pass matching the profile page's existing paper style (`spendly-ui-polish` skill, CSS/markup only)
- [x] 11. Hand the spec's Manual Verification Guide to the developer (Validate)
- [x] 12. `/test-feature 06-date-time-filter`. Fix and re-run until green
- [x] 13. `/code-review-feature 06-date-time-filter`. Fix until the verdict isn't CHANGES REQUESTED
- [x] 14. `.claude/PROGRESS.md`: note Step 6 on the `GET/POST /profile` row and add a Step 6 progress entry. Update the Spendly Field Notes artifact if a new concept came up (e.g. query strings / GET forms)
- [ ] 15. Git finish per the SDD workflow (commit → push → PR → merge), only after 11-13 pass

## Explicitly out of scope

Mirrors the spec's Out of Scope. The items:
- time-of-day filtering and schema changes
- an expenses-list page, full history, pagination
- budget history
- charts, trends and alerts
- category/amount/text filters
- filter UI anywhere except the profile page body (nothing in the `base.html` nav bar)
- keeping the filter across a profile save
- a custom JS calendar
- Steps 7-9

## Verification

Use the spec's own sections; they are not repeated here:
- **Acceptance Criteria** AC1-AC18
- **Manual Verification Guide** (the developer runs it by hand)
- **End-to-End Verification** (`/test-feature` + `/code-review-feature`)

## Revision 1 — budget card, filter redesign, infographic matching (2026-09-20)

### Context (plain words)

**Feature:** Step 6 adds a date filter to the profile page (`/profile`). It's built and tested but not committed yet, on branch `feature/date-time-filter`.

**What came up:** during the manual check, the developer found the budget pieces never appeared. The cause: no account in `database.db` has a monthly budget saved. They then compared the page with two design pictures:
- `static/images/month-by-month-budget-infographic.png`
- `static/images/monthly-budget-add-edit-infographic.png`

**The developer's decisions (2026-09-20):**

| # | What | Decision |
|---|---|---|
| 1 | Money format | `₹10,000.00` everywhere on the profile page: commas added, paise kept |
| 2 | Budget table look | Boxed grid + light-green header row. Applies to the Month-by-month budget table only |
| 3 | Active-range pill | A green pill next to the "Showing 1 Jul – 19 Sep 2026" line, naming the active range ("Last 3 months", "Custom range", …) |
| 4 | New budget card | Below the filter bar, **on the right**. It has 3 states: ① dashed box with "+ Add monthly budget" → ② "₹ [box]" + "Save budget" → ③ "₹10,000" + "✎ Edit" |
| 5 | Budget box in the ✎ Edit profile popup | **Removed.** The card becomes the only place to set the budget |
| 6 | Saving an empty box in the card | **Removes the budget.** The card goes back to state ①, and the budget line and table disappear |
| 7 | Text from the picture | **Only the tip line**, "Your current budget is used for every month in a multi-month view.", is used. The "Set your monthly budget" heading and the "Change it anytime" note are *not* used. (The developer ticked both "Tip line" and "None of them"; I read that as tip line yes, the rest no.) |
| 8 | Filter bar look | Redesigned to match the picture: see Change C |
| 9 | Test data in the real `database.db` | ₹10,000 budget on `shreyanshj249@gmail.com` and `demo@spendly.com`, plus about 6 July/August expenses on demo, so both accounts can show the budget table |

Already done and uncommitted:
- a click anywhere on a From/To box opens the calendar (`static/js/main.js`)
- the `/seed-expense` future-dates bug is logged in `.claude/PROGRESS.md`

### Changes

#### A. Budget card: new behaviour (`database/db.py`, `app.py`, `templates/profile.html`)
- **`database/db.py`:** new `update_monthly_budget(user_id, monthly_budget)` → `UPDATE users SET monthly_budget = ? WHERE id = ?`. `None` clears the budget.
- **`app.py`:** new route `POST /profile/budget`, named `save_budget`:
  1. Login guard: same as `profile()`, i.e. flash + redirect to `/login`.
  2. Read `monthly_budget` and strip commas and spaces, so `10,000` is accepted.
     - Empty → `None`, which removes the budget.
     - Otherwise it must be a number ≥ 0. If not, flash the existing message "Monthly budget must be a non-negative number." (error toast).
  3. Save via `update_monthly_budget`. Flash "Budget saved." or "Budget removed." (success toast).
  4. Redirect back to `/profile` **with the same filter still applied**. Hidden `range`/`start`/`end` inputs in the card's form carry the current filter, and only these three are passed through.
- **`app.py` `profile()` POST (the Edit profile popup):**
  - Stop reading and validating `monthly_budget`.
  - Pass the user's **existing** budget to `update_user`.
  - Without this, saving the popup after removing its budget box would wipe the budget.
- **`profile.html` Edit profile popup:** delete the "Monthly budget (₹)" field.
- **`profile.html` card:** uses the browser's built-in `<details>` open/close box, so no JavaScript is needed.
  - **State ①** (no budget): dashed card. The `<summary>` reads "+ Add monthly budget". Opening it shows the form (**state ②**): a `₹` prefix, a text box with `inputmode="decimal"`, and a "Save budget" button.
  - **State ③** (budget set): the "Monthly budget" title, the big amount `₹10,000.00`, and a `<summary>` "✎ Edit". Opening it shows the same form, pre-filled.
  - The tip line sits under the card: "Your current budget is used for every month in a multi-month view."
- **Layout of the row under the filter bar:**
  - left: the "Showing …" line + pill, the notes, and filter errors
  - right: the budget card
  - on phones, they stack vertically

#### B. Infographic matching (the earlier 3 decisions)
- **Commas:** in `profile.html`, every `₹{{ "%.2f"|format(x) }}` becomes `₹{{ "{:,.2f}".format(x) }}`. This covers the tiles, the budget line, Recent Transactions, By Category, and the budget table.
- **Boxed table:** in `profile.css`, `.budget-table` gets:
  - 1px `var(--border)` lines
  - rounded corners (`var(--radius-md)`)
  - `var(--accent-light)` on the header row

  `.transactions-table` is untouched.
- **Pill:**
  - `app.py` adds `range_label` to the `dashboard` dict, from a key → label map next to `DATE_RANGES`: This month / Last month / Last 3 months / All time / Custom range.
  - `profile.html` adds `<span class="range-pill">` to the "Showing …" line.

#### C. Filter bar redesign (`static/css/profile.css`, minor markup in `profile.html`)
Matching the picture:
- The whole bar is one rounded card: `var(--paper-card)`, 1px `var(--border)`, `var(--radius-lg)`.
- Presets:
  - inactive: light grey fill (`var(--paper-warm)`)
  - active: solid green (`var(--accent)`) with white text (`var(--paper)`)
- A thin vertical divider between the presets and From/To.
- **Apply** is a solid green button.
- It wraps onto two lines on narrow screens.
- Existing tokens only, in `profile.css`. `style.css` isn't touched.

#### D. Test data in the real `database.db` (explicit developer request)
- Run through my own Bash tool, one parameterised script, **not** a `!` block.
- It sets `monthly_budget = 10000` for `shreyanshj249@gmail.com` and `demo@spendly.com`.
- It inserts 6 demo expenses, 3 in July 2026 and 3 in August 2026, all in the past. Each has the description tag **`[step6-test]`** so they're easy to find and delete later.
- Tell the developer exactly what was written. After their check, ask whether to keep or remove it; cleanup is `DELETE … WHERE description LIKE '[step6-test]%'` and resetting the budgets. This follows CLAUDE.md "Verification hygiene".

#### E. Keep the spec and plan in step (`.claude/specs/06-date-time-filter.md`, `.claude/plans/06-date-time-filter.md`)
- **Spec, new FRs:** the budget card + route, removing the popup budget box, commas, the boxed table, the pill, the filter bar look, and the calendar click.
- **Spec, APIs section:** `POST /profile/budget`, with its fields and redirect.
- **Spec, new ACs**, each with a Manual Verification Guide row:
  - AC19: pill
  - AC20: calendar click
  - AC21-AC24: card add, card edit, empty save removes the budget, invalid input shows the error
  - AC25: popup has no budget box, and saving it keeps the budget
- **Spec:** update `₹10000.00` → `₹10,000.00` in the existing examples.
- **Plan:** add the tasks below.

### Order of work (with review stops, per CLAUDE.md's "Session scope" rule)
- [x] 0. Save this plan into the repo: append it to `.claude/plans/06-date-time-filter.md` as a new **"Revision 1 — budget card, filter redesign, infographic matching (2026-09-20)"** section. It carries this Context/decisions table, Changes A-E, and this checklist. From then on, tick boxes **there** after each task
- [x] 1. Test data (D). Tell the developer what was written
- [x] 2. Spec + plan updates (E)
- [x] 3. Budget card behaviour (A): db helper, route, popup change, card markup
- [x] 4. Commas + pill + boxed table (B)
- [x] 5. **STOP:** the developer checks the card and budget table on their own account
- [x] 6. Filter bar redesign (C)
- [x] 7. **STOP:** the developer checks the look against the picture
- [x] 8. `/test-feature 06-date-time-filter`: the test-writer updates the tests from the spec only, then the runner runs them
- [x] 9. `/code-review-feature 06-date-time-filter`
- [x] 10. The developer's final Manual Verification pass — passed 2026-09-20
- [x] 11. Git finish, only on the developer's yes. One PR with everything, including the 3 PNGs and the plain-brief/explorer files — done 2026-09-20, commit `2fb0571`, merged as `4d724ae`

### Verification
- Browser checks on a **throwaway** database: test server on port 5055, screenshots of the card's 3 states, the table and the filter bar, then clean up the server, the database and `.playwright-mcp/`.
- The test-runner passes the whole `tests/test_06-date-time-filter.py`.
- Both reviewers approve.
- The developer's manual pass on their real data from step D.
