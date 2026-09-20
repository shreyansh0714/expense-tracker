# Spec 06 — Date Filter on the Profile Dashboard

> **Partly superseded by `06b-profile-dashboard-restructure.md` (2026-09-20).**
> That spec restructures the profile dashboard and changes three things this
> one pins down: the monthly budget becomes a control on a slim bar rather
> than a card, its `+` and `✎` characters become inline SVG icons, and the
> empty-state text splits into two messages. Every bullet, acceptance
> criterion and verification row affected is marked inline below. Everything
> not marked still stands — in particular FR10 (the range pill) and FR11
> (Indian digit grouping).

## Problem Statement

Everything the profile dashboard (`GET /profile`) shows about money is locked to the
current calendar month. This covers the Total Spent, Transactions and Top Category tiles
and the By Category bars. The Recent Transactions list shows the last 5 expenses ever,
with no date limit. A user cannot look back at last month, a quarter, or their whole
history.

This step adds a date-range filter to the profile dashboard. The user can pick a preset
(This month, Last month, Last 3 months, All time) or a custom From/To range, and every
expense-derived section on the page updates to that range. For ranges longer than one
month, a Month-by-month budget table compares each month's spend to the user's monthly
budget.

**This deliberately overrides spec 04.** `.claude/specs/04-profile-page.md` (Out of
Scope) says: *"Full transaction history, pagination, or filtering of expenses — ... a
real, paginated/filterable expense list belongs solely to the future Expenses/Dashboard
page."* The developer decided on 2026-09-19 that date filtering of the **existing
profile dashboard sections** belongs on `/profile` now. Full history and pagination stay
out of scope (see Out of Scope).

"Date-time filter" means filtering by **calendar date only**. `expenses.date` stores
`YYYY-MM-DD` with no time of day, and this step adds none.

## Functional Requirements

1. **Filter bar placement:** the filter bar (the 4 preset buttons plus the From/To/Apply
   custom range) appears **only inside `templates/profile.html`**, in the page body
   directly above the stat tiles. It must **not** be added to the nav bar in `base.html`,
   the footer, the edit-profile modal, or any other page or template.
   It is built as two plain HTML `<form method="get">` forms, both targeting
   `url_for('profile')`: one holds the preset buttons, the other holds the custom range
   (with a hidden `range=custom`). They are separate so that pressing Enter in a date box
   submits the custom range and not the first preset button:
   - Four preset buttons: **This month**, **Last month**, **Last 3 months**, **All time**.
   - A custom range made of two native `<input type="date">` fields, labelled **From**
     and **To**, plus an **Apply** button. The browser's own calendar dropdown is the
     date picker; there is no custom JS calendar. The display format follows the
     browser/OS locale (dd/mm/yyyy on an Indian-English setup).
   - The active preset is visually marked and carries `aria-pressed="true"`. When a
     custom range is active, From/To are pre-filled with the effective dates.
2. **Range state lives in the URL** as query parameters, so a refresh or bookmark keeps
   it (see APIs).
3. **Preset definitions** (today = the server's local date):
   | Preset | `range=` | Start | End |
   |---|---|---|---|
   | This month (default) | `this_month` | 1st of current month | today |
   | Last month | `last_month` | 1st of previous month | last day of previous month |
   | Last 3 months | `last_3_months` | 1st of the month 2 months before the current one (e.g. on 19 Sep 2026: 1 Jul 2026) | today |
   | All time | `all_time` | history start (see 5) | today |
   | Custom | `custom` | `start` param | `end` param |
   Both ends are **inclusive**.
4. **Sections that follow the range**:
   - Total Spent tile: sum of `amount` in range.
   - Transactions tile: count of expenses in range.
   - Top Category tile and the By Category bars: category totals in range.
   - Recent Transactions: the **5 most recent** expenses in range (still a 5-row preview),
     newest first.
   - A line of text above the tiles saying what is shown, e.g.
     `Showing 1 Jul 2026 – 19 Sep 2026`, with dates formatted `%d %b %Y`.
5. **History start.** A user's *history start* is the **earlier** of (a) the date part of
   `users.created_at` and (b) the user's oldest `expenses.date`. If the user has no
   expenses, it is (a). This means an expense dated before signup is never hidden.
6. **Range adjustment rules** (the "bank-app" behaviour). Rules (c)-(e) only apply to
   custom ranges. Presets can never be invalid or in the future. The **notes** in (a) and
   (b) are shown **only for custom ranges**, decided by the developer on 2026-09-19. For
   presets, (a) silently moves the "Showing …" line's start to history start. (b) shows
   the preset's own dates with empty results and no note. This keeps a brand-new user's
   default This month view free of notes:
   | Case | Behaviour |
   |---|---|
   | (a) Start is before history start and end is on/after it | Start moves to history start. The note reads `Showing data from <history start>, when your records begin.` |
   | (b) Whole range is before history start | Empty result (₹0, 0 transactions, no top category, empty list/bars, no budget table). The note reads `Your records begin on <history start> — there's no data before that.` |
   | (c) Whole range is in the future (start after today) | Filter error `That date range is in the future.` The page falls back to This month |
   | (d) Start on/before today, end after today | End moves to today. No message |
   | (e) Invalid custom input | Filter error (texts below). The page falls back to This month |
7. **Budget comparison**:
   - If the effective range falls within **one calendar month** and the user has a
     `monthly_budget`, the existing `₹<spent> of ₹<budget> budget used` subtext under Total Spent is shown
     (today's behaviour).
   - If the effective range spans **more than one calendar month** and the user has a
     `monthly_budget`, that subtext is hidden. A **Month-by-month budget** table is shown
     instead, with one row per calendar month touched by the range, oldest month first.
     Columns: **Month** (`Jul 2026`), **Budget** (current `monthly_budget`), **Spent** (that
     month's spend, limited to the range), **% used** (rounded to a whole number).
     A month with no spend shows `₹0.00` and `0%` (the FR11 format).
   - Every row uses the **current** `monthly_budget`, because budget history is not
     stored. The table carries the caption `Uses your current monthly budget for every
     month.`
   - With no `monthly_budget` set, neither the subtext nor the table is shown.
8. **The edit-profile modal loses its budget box** (Revision 1, 2026-09-20). The
   "Monthly budget (₹)" field is removed from the ✎ Edit profile popup, because the
   budget card (FR9) is now the only place to set it. Saving the popup keeps the user's
   existing `monthly_budget` unchanged. Otherwise it works as before: saving redirects
   to plain `/profile` (This month), a POST that fails validation re-renders the page
   with This month stats, and the filter is not preserved across a profile save.

*FR9-FR13 were added in Revision 1 (2026-09-20), after the developer compared the page
with `static/images/month-by-month-budget-infographic.png` and
`static/images/monthly-budget-add-edit-infographic.png`. Those pictures set the look
only; the only text taken from them is the tip line in FR9.*

9. **Budget card**, on `/profile` only, directly below the filter bar on the **right**.
   The "Showing …" line, pill, notes and filter errors sit on the left of the same row,
   and on narrow screens the two stack. It has three states:
   - **① No budget:** **[Superseded by spec 06b.]** Now a bar control reading **Add monthly
     budget** preceded by a plus icon. Originally: a card with an **+ Add monthly budget** control. It uses the
     page's existing hand-drawn border treatment, like the stat tiles and the other
     cards. The infographic's dashed green outline is an **annotation** marking where
     the card sits, not part of the card, so it is not copied (developer's call,
     2026-09-20: the dashed green version "feels very out of place").
   - **② Entering:** **[Superseded by spec 06b.]** The form now opens as a popover over the
     page rather than expanding the card. Originally: opening ① (or ③'s **✎ Edit**) reveals a form with a `₹` prefix, a
     text box named `monthly_budget`, and a **Save budget** button. It uses the
     browser's built-in `<details>`, so it needs no JavaScript.
   - **③ Budget set:** **[Superseded by spec 06b.]** Now the amount on the bar followed by a
     control reading **Edit** preceded by a pencil icon; no card, no title.
     Originally: same card treatment, the title **Monthly budget**, the amount in the FR11 format
     (e.g. `₹10,000.00`), and an **✎ Edit** control. The box is pre-filled.
   - Under the card, always: the tip line `Your current budget is used for every month
     in a multi-month view.` **[Superseded by spec 06b.]** The sentence is unchanged but now
     renders **inside** the Add/Edit popover, above the form.
   - Saving: commas and spaces are ignored (`10,000` = `10000`).
     - An **empty** box removes the budget: back to state ①, and the budget subtext
       and table disappear. Toast: `Budget removed.`
     - A number ≥ 0 is saved. Toast: `Budget saved.`
     - Anything else is not saved. Error toast: `Monthly budget must be a
       non-negative number.`
     - Every outcome returns to `/profile` with the **same filter** still applied.
10. **Active-range pill:** a green pill inside the "Showing …" line, naming the active
    range: `This month`, `Last month`, `Last 3 months`, `All time` or `Custom range`.
    After an error fallback, it says `This month`. It is rendered as
    `<span class="range-pill">…</span>`, so a test can read it even though the preset
    buttons carry the same words.
11. **Money format:** every ₹ amount on the profile page uses **Indian digit grouping**
    with 2 decimals (developer's call, 2026-09-20): the last 3 digits are one group and
    everything above them is grouped in 2s. Examples: `₹89.99`, `₹1,000.00`,
    `₹10,000.00`, `₹1,00,000.00`, `₹12,34,567.50`, `₹1,23,45,678.00`. This covers the
    tiles, the budget subtext, Recent Transactions, By Category, the budget table and
    the budget card. Python's `{:,.2f}` gives international grouping
    (`1,234,567.50`), so it must not be used for display.
12. **Look (from the pictures):**
    - The filter bar is one rounded, bordered card. Inactive presets have a light grey
      fill; the active preset is solid green with white text. A thin divider separates
      the presets from From/To, and **Apply** is a solid green button.
    - The Month-by-month budget table is a boxed grid with a light-green header row.
      Recent Transactions keeps its current plain look.
13. **Calendar click:** clicking anywhere on a From/To box, not just its small calendar
    icon, opens the browser's calendar.

## APIs

`GET /profile` (existing route, login required, same as today)

| Query param | Allowed values | Missing / empty |
|---|---|---|
| `range` | `this_month`, `last_month`, `last_3_months`, `all_time`, `custom` | Treated as `this_month`, with no error |
| `start` | `YYYY-MM-DD` (native date inputs submit ISO) | Only read when `range=custom` |
| `end` | `YYYY-MM-DD` | Only read when `range=custom` |

- Response: always `200`, rendering `profile.html`. Invalid filter input never produces a
  4xx. It shows a filter error and falls back to This month.
- Filter error messages (exact text, shown in a filter-error area next to the filter
  bar, separate from the existing edit-profile `error` banner):
  | Input | Message |
  |---|---|
  | `range` not in the allowed list | `Unknown date range.` |
  | `range=custom` with `start` or `end` missing/empty | `Please choose both a start and an end date.` |
  | `start` or `end` not a real `YYYY-MM-DD` date (e.g. `2026-02-30`, `abc`) | `Please enter valid dates.` |
  | `start` after `end` | `Start date must be on or before end date.` |
  | `start` after today | `That date range is in the future.` |
- New template context (in addition to the existing variables):
  - `active_range`: the preset key actually applied (`this_month` after a fallback)
  - `range_start`, `range_end`: effective `date` objects (for the "Showing …" line and
    From/To pre-fill)
  - `range_note`: the case (a)/(b) note text or `None`
  - `filter_error`: an error message or `None`
  - `monthly_budget_rows`: a list of `{month_label, budget, spent, percent}`, empty unless
    the table rule in FR7 applies
- **`POST /profile/budget`** (new in Revision 1, login required: logged out → flash
  + redirect to `/login`, same as `/profile`)
  | Form field | Meaning |
  |---|---|
  | `monthly_budget` | The budget. Commas/spaces ignored; empty = remove the budget |
  | `range`, `start`, `end` | Hidden fields that carry the current filter, so the redirect keeps it |
  - Response: always a `302` redirect to `/profile`, with the same `range`/`start`/`end`
    query params (only those three), plus a toast (see FR9).
- DB data shape: `expenses.date` is `YYYY-MM-DD` text, so range queries use string
  comparison `date >= ? AND date <= ?` with ISO strings (parameterised).

## Files and Interfaces Involved

| File | Change |
|---|---|
| `database/db.py` | Generalise `get_monthly_category_totals(user_id)` and `get_monthly_transaction_count(user_id)` to take `start, end` (inclusive ISO dates) instead of computing the current month internally. This also removes their duplicated month-range code. `get_recent_expenses(user_id, limit=5)` gains an optional `start, end` bound. Add `get_first_expense_date(user_id)` (returns `MIN(date)` or `None`) and a per-month spend helper (`GROUP BY substr(date, 1, 7)`) for the budget table. Exact names are for the plan to decide. `/profile` is the only caller of these helpers. |
| `app.py` | `profile()` reads `request.args`, resolves the effective range (presets, validation, adjustment rules), and passes the new context to all three `render_template("profile.html", …)` calls (GET, validation-error POST, IntegrityError POST). The range-resolving logic is a plain helper function in `app.py`, with no DB access inside it. |
| `templates/profile.html` | Adds the filter bar, filter-error area, "Showing …" line, range note, and the Month-by-month budget table. The empty-state texts change from month wording (`No expenses logged this month yet.`, `No expenses logged yet.`) to `No expenses in this period.` **[Superseded by spec 06b.]** Spec 06b FR8 splits this into two messages: `You haven't logged any expenses yet.` when the account has never logged one, and `No expenses between <start> and <end>. Try a wider range.` when a filter matched nothing. |
| `static/css/profile.css` (new) | Styles for the filter bar, active preset, and budget table only, using existing `:root` tokens. Linked from `profile.html` via `{% block head %}`. Existing profile styles stay in `style.css` |
| `.claude/PROGRESS.md` | The `GET/POST /profile` row notes Step 6 once it's built |
| Revision 1: `database/db.py` | New `update_monthly_budget(user_id, monthly_budget)` (`None` clears it) |
| Revision 1: `app.py` | New `POST /profile/budget` route. `profile()` POST no longer reads `monthly_budget` and keeps the saved value. `range_label` added to the template context |
| Revision 1: `templates/profile.html`, `static/css/profile.css`, `static/js/main.js` | Budget card, pill, comma money format, boxed budget table, filter-bar look, budget field removed from the popup. `main.js`: calendar opens on click |

## Constraints

- Flask + sqlite3 + vanilla JS only. No new pip packages, no JS date library, no custom
  calendar widget (the native `<input type="date">` is the decided picker).
- All SQL goes through `database/db.py` with `?` placeholders. No f-string SQL.
- The filter is a GET form built with `url_for('profile')`. It needs no JavaScript to
  work.
- Date math uses Python's `datetime`/`date` stdlib. "Today" is `date.today()`, the same
  as the existing month helpers.
- Styling follows the existing profile page and `spendly-ui-polish` look. For
  Revision 1, the two infographics in `static/images/` are the look reference. Colors, spacing and fonts come from `:root` tokens.
- **Session scope** (CLAUDE.md): build in reviewed pieces rather than one pass:
  (1) DB helpers + range resolving + filter bar with the filtered tiles/list/bars,
  (2) edge-case notes/errors, (3) budget table, (4) styling.

## Out of Scope

- Filtering by time of day, or any schema change to `expenses`.
- A separate expenses-list page, full transaction history, or pagination. Recent
  Transactions stays a 5-row preview.
- Budget history. The table uses the current `monthly_budget` for every month.
- Charts, trends, month-over-month comparisons, and budget alerts. These stay with the
  future Dashboard (`.claude/PROGRESS.md` Future Features).
- Filtering by category, amount, or text.
- Any filter UI outside the profile page body: nothing goes in the nav bar
  (`base.html`), the footer, the edit-profile modal, or other pages.
- Keeping the chosen filter across an edit-profile save.
- A custom JS calendar or a forced `dd/mm/yy` display format.
- Adding/editing/deleting expenses (Steps 7-9).

## Edge Cases and Error Handling

| Situation | Handling |
|---|---|
| No query params | This month, no error, no note |
| `range=bogus` | `Unknown date range.` + This month |
| `range=custom` with one or both dates empty | `Please choose both a start and an end date.` + This month |
| Malformed/impossible date (`2026-02-30`, `19/09/2026`, `abc`) | `Please enter valid dates.` + This month |
| `start` > `end` | `Start date must be on or before end date.` + This month |
| `start` > today | `That date range is in the future.` + This month |
| `end` > today, `start` ≤ today | End moves to today silently |
| Custom range: start before history start, end on/after it | Start moves; note `Showing data from <date>, when your records begin.` |
| Custom range entirely before history start | Empty result + note `Your records begin on <date> — there's no data before that.` |
| `start == end` (a single day) | Valid. Shows that day only |
| User has zero expenses | History start = signup date. Every range shows ₹0 / 0 / empty states. No crash |
| Range with data in some months only | Budget table rows for empty months show ₹0 / 0% |
| `monthly_budget` is NULL | No subtext, no table |
| `monthly_budget` is `0` | Table rows show `—` in % used (no division by zero) |
| Preset range starts before history start (e.g. new user on This month) | No note. The "Showing …" start moves to history start |
| Preset range entirely before history start (e.g. new user on Last month) | No note. Empty states |
| `range=custom` with `start`/`end` given AND `range` preset ≠ custom | `start`/`end` are ignored. The preset wins |
| Extra unknown query params | Ignored |
| Logged-out visit to `/profile?range=…` | Existing behaviour: flash + redirect to `/login` |

## Acceptance Criteria

Assume today = 2026-09-19 in the examples. Tests should compute dates relative to
`date.today()`.

- [x] AC1: `GET /profile` with no params returns 200 and shows current-month figures, with the This month preset marked `aria-pressed="true"`.
- [x] AC2: The page contains GET forms with 4 preset buttons (`range` values `this_month`, `last_month`, `last_3_months`, `all_time`) and two `<input type="date">` fields named `start` and `end`, plus an Apply button submitting `range=custom`.
- [x] AC3: `?range=last_month` totals/counts/categories include only expenses dated in the previous calendar month.
- [x] AC4: `?range=last_3_months` includes expenses from the 1st of the month two months back through today, and excludes one dated the day before that.
- [x] AC5: `?range=all_time` includes every one of the user's expenses, including one dated before `users.created_at`.
- [x] AC6: `?range=custom&start=X&end=Y` includes expenses dated exactly `X` and exactly `Y` (inclusive) and excludes `X-1` and `Y+1`.
- [x] AC7: Recent Transactions shows at most 5 rows, all within the range, newest first.
- [x] AC8: Another user's expenses never appear in any filtered figure.
- [x] AC9: Each error input in the APIs error table returns 200, shows its exact message, and shows This month figures.
- [x] AC10: A custom range starting before history start shows `Showing data from <date>, when your records begin.` and the correct figures from history start.
- [x] AC11: A custom range entirely before history start shows `Your records begin on <date> — there's no data before that.` and ₹0 / 0 / empty states.
- [x] AC12: A custom range with `end` in the future and `start` in the past returns 200 with no error, and the "Showing …" line ends at today.
- [x] AC13: With a `monthly_budget` set, a single-month range shows the `₹<spent> of ₹<budget> budget used` subtext and no budget table. A multi-month range hides that text and shows the Month-by-month budget table with one row per month, oldest first, correct Spent and % used, and the caption `Uses your current monthly budget for every month.`
- [x] AC14: With no `monthly_budget`, no budget subtext or table appears for any range.
- [x] AC15: **[Superseded by spec 06b.]** Replaced by spec 06b AC16/AC17 (two distinct messages). Originally: Empty ranges show `No expenses in this period.` in both Recent Transactions and By Category.
- [x] AC16: Submitting the edit-profile modal still works and redirects to `/profile` (This month).
- [x] AC17: The date input's calendar dropdown opens in a real browser when clicked (manual only).
- [x] AC18: The filter form (preset buttons, `start`/`end` date inputs) appears on `/profile` only. `base.html` is unchanged by this step, and the rendered HTML of `/`, `/login`, `/register`, `/terms` and `/privacy` contains no `name="range"` element.
- [x] AC19: The `<span class="range-pill">` in the "Showing …" line holds the active range's name: `This month` by default, `Last 3 months` for `?range=last_3_months`, `Custom range` for a valid custom range, and `This month` after an error fallback.
- [x] AC20: Clicking anywhere on a From/To box opens the browser's calendar (manual only).
- [x] AC21: **[Superseded by spec 06b.]** The `+` and `✎` are now inline SVG icons, so the literal text is `Add monthly budget` and `Edit`; the card is now a bar. The save behaviour, the `10000` value and the `Budget saved.` toast are unchanged. Originally: With no budget, `/profile` shows `+ Add monthly budget`. POSTing `monthly_budget=10,000` to `/profile/budget` saves `10000`, redirects to `/profile`, shows `Budget saved.`, and the card then shows `₹10,000.00` with `✎ Edit`.
- [x] AC22: **[Superseded by spec 06b.]** Literal text is now `Add monthly budget` (the `+` is an icon). Removal behaviour and the `Budget removed.` toast are unchanged. Originally: POSTing `monthly_budget=` (empty) to `/profile/budget` removes the budget, shows `Budget removed.`, and the card shows `+ Add monthly budget` again.
- [x] AC23: POSTing `monthly_budget=-5` or `abc` to `/profile/budget` leaves the budget unchanged and shows `Monthly budget must be a non-negative number.`
- [x] AC24: POSTing to `/profile/budget` with `range=last_3_months` redirects to `/profile?range=last_3_months`. A logged-out POST redirects to `/login`.
- [x] AC25: The ✎ Edit profile popup has no `monthly_budget` field, and saving the popup (e.g. changing the name) keeps an existing budget unchanged.
- [x] AC26: Amounts use Indian grouping: `₹10,000.00` for ten thousand, `₹1,00,000.00` for one lakh and `₹12,34,567.50` for that amount, in the budget subtext, table, tiles and card.

## Manual Verification Guide

**Setup (once):**
1. In a terminal inside `expense-tracker/`, run `source venv/bin/activate` then `python app.py`. Leave it running.
2. In a **second** terminal, give the demo account expenses across several months: run the `/seed-expense` command in Claude Code for `demo@spendly.com`, spreading them over the last 4 months. (This writes real rows into `database.db`. That's expected for manual testing.)
3. Open `http://localhost:5001/login` and sign in as `demo@spendly.com` / `demo123`.
4. To see the true numbers any time, run this read-only query in the second terminal, changing the two dates to match the range you're checking:
   `sqlite3 database.db "SELECT COUNT(*), SUM(amount) FROM expenses WHERE user_id=(SELECT id FROM users WHERE email='demo@spendly.com') AND date BETWEEN '2026-09-01' AND '2026-09-19';"`
   It prints `count|total`, e.g. `12|8450.0`.

| AC | How to check by hand | Expected |
|---|---|---|
| AC1 | Visit `http://localhost:5001/profile` | Page loads. The "This month" button looks active. Right-click it → Inspect → the element shows `aria-pressed="true"`. Total Spent matches the step-4 query for `2026-09-01`..today |
| AC2 | Look at the filter bar above the tiles | 4 buttons (This month, Last month, Last 3 months, All time), a From box, a To box, and an Apply button |
| AC3 | Click **Last month**. Check the URL bar | URL ends `?range=last_month`. Total Spent and Transactions match the step-4 query for `2026-08-01`..`2026-08-31` |
| AC4 | Click **Last 3 months** | "Showing 1 Jul 2026 – 19 Sep 2026" (with today's date). Figures match the query for `2026-07-01`..today |
| AC5 | Click **All time** | Transactions equals `sqlite3 database.db "SELECT COUNT(*) FROM expenses WHERE user_id=(SELECT id FROM users WHERE email='demo@spendly.com');"` |
| AC6 | Click the From box → the calendar opens → pick a date that has an expense. Pick the same date in To, then click Apply | Only that day's expenses are counted. Compare with the query using that date twice |
| AC7 | With All time selected, look at Recent Transactions | At most 5 rows, newest date at top |
| AC8 | Register a second account in a private window and look at its `/profile?range=all_time` | ₹0 and 0 transactions, none of the demo account's expenses |
| AC9 | Paste each URL, one by one: `/profile?range=bogus` · `/profile?range=custom&start=2026-09-01` · `/profile?range=custom&start=abc&end=2026-09-10` · `/profile?range=custom&start=2026-09-10&end=2026-09-01` · `/profile?range=custom&start=2030-01-01&end=2030-01-31` | Each shows its message from the spec's error table, in that order: `Unknown date range.` · `Please choose both a start and an end date.` · `Please enter valid dates.` · `Start date must be on or before end date.` · `That date range is in the future.`. The page still loads and This month is active |
| AC10 | Visit `/profile?range=custom&start=2000-01-01&end=2026-09-19` | Note `Showing data from <oldest expense or signup date>, when your records begin.` Figures equal All time |
| AC11 | Visit `/profile?range=custom&start=2000-01-01&end=2000-12-31` | Note `Your records begin on <date> — there's no data before that.` ₹0, 0, `No expenses in this period.` _Superseded by 06b: read `No expenses in this period.` as `No expenses between <start> and <end>. Try a wider range.` (06b FR8)._ |
| AC12 | Visit `/profile?range=custom&start=2026-09-01&end=2030-12-31` | No error. The "Showing …" line ends at today's date |
| AC13 | Make sure the budget card (right, under the filter bar) shows `₹10,000.00` (use the card to set it if not). Click **Last month**, then **Last 3 months** | Last month: `₹<last month's total> of ₹10,000.00 budget used` under Total Spent, no table. Last 3 months: no subtext, a table with rows Jul 2026, Aug 2026, Sep 2026, and the caption. Each row's Spent matches the query for that month |
| AC14 | In the budget card click **✎ Edit**, empty the box, **Save budget**. Click Last 3 months | No budget text, no table _Superseded by 06b: read **✎ Edit** as the bar's **Edit** control (06b FR3)._ |
| AC15 | Visit the AC11 URL | Both sections say `No expenses in this period.` _Superseded by 06b: read `No expenses in this period.` as `No expenses between <start> and <end>. Try a wider range.` (06b FR8)._ |
| AC16 | While on `?range=last_month`, open Edit profile and change your name → Save | You land on `/profile` (no `?range=`), with the "Profile updated." message |
| AC17 | Click the From box in Chrome | A calendar dropdown appears. Picking a day fills the box |
| AC18 | Look at the nav bar at the top of `/profile`, then visit `/`, `/terms`, `/privacy`. Also run `git diff main -- templates/base.html` | The filter buttons appear only in the profile page body, above the tiles, and never in the nav bar or on the other pages. The `git diff` command prints nothing |
| AC19 | Click **Last 3 months**, then paste `/profile?range=bogus` | A green pill reading `Last 3 months` in the "Showing …" line; after the bogus URL, it reads `This month` |
| AC20 | Click the **middle** of the From box, on the `dd/mm/yyyy` text, not the icon | The calendar opens |
| AC21 | Log in as an account with no budget. In the card on the right, click **+ Add monthly budget**, type `10,000`, click **Save budget** | Green toast `Budget saved.` The card shows `₹10,000.00` and **✎ Edit** _Superseded by 06b: read **+ Add monthly budget** as the bar's **Add monthly budget** control (06b FR3)._ |
| AC22 | Click **✎ Edit**, empty the box, click **Save budget** | Toast `Budget removed.` The card shows **+ Add monthly budget** again, and the budget line under Total Spent is gone _Superseded by 06b: read **✎ Edit** as the bar's **Edit** control (06b FR3)._ |
| AC23 | Open the card's form, type `-5`, save. Then try `abc` | Red toast `Monthly budget must be a non-negative number.` each time, and the budget is unchanged |
| AC24 | Click **Last 3 months**, then save a budget from the card | You land back on `/profile?range=last_3_months`, not This month |
| AC25 | Open **✎ Edit profile** | No "Monthly budget" field. Change your name and save: the budget card still shows the same amount |
| AC26 | Set the budget to `1234567.5` in the card, then look at the card and the budget table | The card reads `₹12,34,567.50` (Indian grouping: last 3 digits, then 2s), not `₹1,234,567.50` |

**Cleanup:** the `/seed-expense` rows from setup step 2 stay in `database.db`. Delete
them only if you don't want them for later steps.

## End-to-End Verification

1. `venv/bin/python -m pytest tests/test_06-date-time-filter.py -v` (written by
   `/test-feature 06-date-time-filter`). All tests pass. The tests insert their own
   dated expenses through the `auth_client` fixture's throwaway DB and never touch
   `database.db`.
2. Run the Manual Verification Guide above end to end in a browser. Every row matches.
3. `/code-review-feature 06-date-time-filter` returns APPROVED or APPROVED WITH SUGGESTIONS.
