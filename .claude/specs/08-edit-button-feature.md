# Spec 08 — Edit expense (pencil button + edit page)

**Status:** Draft — not yet implemented
**Branch:** `feature/edit-button-feature` (branched off `main` at `e8c2113`)
**Date:** 2026-09-23

**Order note:** Step 9 (Delete expense) was built before this step, by the
developer's choice. Step 9 already added the Actions column to Recent
Transactions with only a trash button. Its spec says: "Step 8 adds its edit
button next to it later." This step adds that button.

**Design reference:** none (confirmed in the interview). The edit page reuses
the Add expense page's look (`templates/add_expense.html` +
`static/css/add_expense.css`). Any later visual polish must not add, remove or
reword the content listed here (CLAUDE.md, "Mockup content convention").

---

## 1. Problem Statement

Since Step 7 a user can add expenses, and since Step 9 they can delete them,
but they can't fix one. A wrong amount, the wrong category or a mistyped date
can only be corrected by deleting the expense and adding it again.
`/expenses/<id>/edit` is a stub in `app.py` (lines 474-476) that returns the
plain string `"Edit expense — coming in Step 8"`. It has no login check, and
nothing links to it.

This step makes editing an expense a real feature:

1. A pencil button on every row of the **Recent Transactions** table on
   `/profile`, next to the trash button.
2. An **Edit expense** page, pre-filled with the expense's current amount,
   category, date and description, using the same rules as Add expense.
   Above the form it shows the budget line, the original values, and when
   the expense was last edited.
3. On **Save changes**: the expense is updated and its new `updated_at`
   time is stored. The user lands back on `/profile` with the **same date
   filter** they were viewing, an "Expense updated." toast, and the edited
   row highlighted.
4. Rows that have ever been edited show a small yellow circle badge (with a pencil) in front
   of the date in Recent Transactions.

## 2. Functional Requirements

### Database — `database/db.py`

- **FR1 — New column.** The `expenses` table gets `updated_at TEXT`,
  nullable, with no default. `NULL` means the expense was never edited.
  - The `CREATE TABLE IF NOT EXISTS expenses` statement in `init_db()`
    includes it, for new databases.
  - Existing databases get it through the same idempotent `ALTER TABLE ...
    ADD COLUMN` + `except sqlite3.OperationalError: pass` pattern `init_db()`
    already uses for `users.monthly_budget`/`users.notes`. Existing rows keep
    `updated_at = NULL`. No other data changes.
- **FR2 — `get_expense(user_id, expense_id)`.** Returns the row (all columns)
  from `SELECT * FROM expenses WHERE id = ? AND user_id = ?`, or `None`.
- **FR3 — `update_expense(user_id, expense_id, amount, category, date,
  description)`.** Runs
  `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ?,
  updated_at = datetime('now') WHERE id = ? AND user_id = ?`, commits, and
  returns `cur.rowcount == 1`. `updated_at` is UTC, the same as
  `created_at`.

### The button — `/profile` Recent Transactions table

- **FR4 — Pencil link per row.** Every row's last cell gets an
  `<a class="row-edit-btn" aria-label="Edit expense">` **before** the
  existing trash button:
  - Content: the existing `icons.edit()` macro from `templates/_icons.html`.
    No visible text.
  - `href` = `url_for('edit_expense', id=expense.id, **current filter)`.
    The current filter is `range=<active_range>`, plus `start` and `end`
    (ISO dates) when `active_range == 'custom'`. These are the same values
    the delete popup's hidden inputs already carry.
  - It's a plain link (GET), with no JavaScript.
- **FR5 — Column width.** The Actions column (`static/css/profile.css`,
  `.transactions-table th:last-child`, currently `width: 2.5rem`) widens to
  fit both icons side by side, in one line. `.row-edit-btn` looks like
  `.row-delete-btn` (same padding, radius and muted colour), but its hover
  uses `--accent`/`--accent-light` (or the nearest existing accent tokens)
  instead of the danger colours.
- **FR6 — Edited badge.** When `expense.updated_at` is set, the Date cell
  starts with a `<button type="button" class="edited-badge">` holding
  `icons.edit(10)` (a small dark `--ink` pencil) inside a filled yellow
  (`--sticky`) circle, so it can't be mistaken for the row's plain pencil
  edit button. It sits in a gutter on the left of the Date column. Every row
  and the header keep that gutter, so the dates stay lined up and the
  description column isn't narrowed. Rows never edited show no badge.
  - **Instant tooltip:** hovering (or keyboard-focusing) the badge shows,
    with no delay, a small dark tooltip `Edited <D Mon YYYY, h:mm AM/PM> ·
    click for history`, drawn with CSS (`data-tooltip` + `::after`), not the
    browser's delayed `title` tooltip.
  - `aria-label="Edited <same time>, show edit history"`.
  - Clicking it opens the edit-history popup (FR22).
  - *(Changed 2026-09-23 at the developer's request: first an "edited" text
    tag, which the Description column's "…" cut off; then a plain pencil,
    which looked like the edit button; then a `title` tooltip, which
    appeared only after a delay.)*
- **FR7 — Nothing else changes on the page.** Other cards, the delete
  popup, the empty states and the Step 7 green new-row highlight stay as
  they are.

### The edit page — `GET /expenses/<int:id>/edit`

- **FR8 — Login required.** No `user_id` in the session → flash
  `Please sign in to edit an expense.` (category `error`) and redirect to
  `url_for('login')`. The same applies to POST (FR13).
- **FR9 — Own expenses only.** The route calls
  `get_expense(session["user_id"], id)`. `None` → `abort(404)`, the same for
  "doesn't exist" and "belongs to someone else".
- **FR10 — Page content, top to bottom** (rendered from
  `templates/add_expense.html`, so both pages share one form; see §4):
  1. Title **Edit expense**, subtitle **Fix a mistake in something you
     logged.**
  2. The **budget line**, exactly as on Add expense:
     `₹<spent> of ₹<budget> used this month`, or `No monthly budget set`.
  3. **Original values** (read-only, always taken from the database, never
     from what was typed): a line
     `Currently: <date> · <category> · ₹<amount> · <description>`, where
     `<description>` is `—` when empty and `<amount>` uses the `inr` filter.
  4. **Edited-on** (read-only): `Last edited <YYYY-MM-DD>`, the date part
     of `updated_at`, or `Never edited` when it's `NULL`.
  5. The form, `method="POST"`,
     `action="{{ url_for('edit_expense', id=expense.id) }}"`, with the same
     four fields, names, types, limits and category list as Add expense
     (`amount`, `category`, `date` with `max=today`, `description` with
     `maxlength=200`). Its fields are pre-filled with the stored values: the
     amount shown as a plain number such as `250.0` or `1250.5`, and an empty
     description left empty.
  6. Hidden inputs `range`, `start`, `end`, holding whichever of those GET
     query args were present (only the non-empty ones).
  7. A **Save changes** submit button and a **Cancel** link to
     `url_for('profile', **those same filter args)`.
- **FR11 — Add expense unchanged.** `/expenses/add` still renders the same
  title, subtitle, form action, button label (**Add expense**) and fields
  as before, with no original-values or edited-on lines.

### Saving — `POST /expenses/<int:id>/edit`

- **FR12 — Methods.** The route accepts `GET` and `POST`.
- **FR13 — Guard + ownership.** The login check (FR8) and the
  `get_expense` → `abort(404)` check (FR9) run first. Nothing is written if
  either fails.
- **FR14 — Validation.** The same 7 checks, in the same order, with the
  same messages as Add expense (Step 7 FR6). Stop at the first failure:
  1. `Please enter an amount.`
  2. `Amount must be a number greater than 0.`
  3. `Amount can't be more than ₹1,00,00,000.00.`
  4. `Please choose a category.`
  5. `Please enter a valid date.`
  6. `Date can't be in the future.`
  7. `Description must be 200 characters or fewer.`
- **FR15 — Error re-render.** On a validation error, the page re-renders
  with status **200**, the error message, the values the user typed, the
  original-values and edited-on lines (still from the database), and the
  filter hidden inputs. Nothing is written.
- **FR16 — No changes.** If the cleaned values equal what's stored (amount
  after rounding to 2 decimals, the category, the date, and the description
  after stripping, with empty treated as `NULL`):
  - `update_expense` is **not** called and `updated_at` is **not** changed.
  - Flash `No changes to save.` (category `success`) and redirect to
    `url_for('profile', **filter_args)`. No row highlight.
- **FR17 — Success.** Otherwise:
  - call `update_expense(...)`. If it returns `False` (the row vanished
    between load and save), `abort(404)`.
  - set `session["new_expense_id"] = id`. This reuses the Step 7 highlight:
    `/profile` pops it and gives that row `class="row-new"`.
  - flash `Expense updated.` (category `success`).
  - redirect to `url_for('profile', **filter_args)`. `filter_args` comes
    from the form's `range`/`start`/`end`, exactly as `delete_expense()`
    and `save_budget()` build it (only non-empty keys). With none, it
    redirects to plain `/profile`.

### After saving — `/profile`

- **FR18 — Page reflects the edit.** The row shows the new values and the
  edited badge. The stat tiles, By Category, the range+budget bar and the
  monthly budget table all use the new values (they query the DB on every
  load). If the new date is outside the current filter, the row isn't
  shown. The toast still appears.

### Added after Build (developer request, 2026-09-23)

- **FR19 — Scroll to the edited row.** Every Recent Transactions `<tr>` gets
  `id="expense-<id>"`. The success (FR17) and no-changes (FR16) redirects
  add the anchor `#expense-<id>` to the URL, e.g.
  `/profile?range=this_month#expense-42`, so the browser scrolls that row
  into view by itself (no JS). The rows get a `scroll-margin-top` so the
  sticky navbar doesn't cover the row. If the row isn't on the page (its new
  date is outside the filter), the page just stays at the top.
- **FR20 — Back arrow never shows a stale edit form.** On the edit page, the
  `<form>` gets `id="edit-expense-form"` and
  `data-back-to="<profile URL with the filter + #expense-<id>>"`. The Cancel
  link uses the same URL. A new IIFE in `static/js/main.js` (guarded by
  `if (!form) return;`) listens for `pageshow`. When the page was reached
  with the browser's Back/Forward buttons (`event.persisted`, or the
  navigation entry's `type === "back_forward"`), it calls
  `location.replace(data-back-to)`. Result: pressing Back after saving (or
  after Cancel) lands on a fresh `/profile`, scrolled to that row, never on
  the old edit form. A normal click on the pencil, or a refresh, is
  unaffected.

### Edit history (added 2026-09-23, developer request)

- **FR21 — History table.** A new table, created in `init_db()` with
  `CREATE TABLE IF NOT EXISTS`:
  ```sql
  expense_edits (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      expense_id INTEGER NOT NULL,
      edited_at TEXT NOT NULL,          -- UTC, same value as expenses.updated_at
      old_amount REAL NOT NULL,   new_amount REAL NOT NULL,
      old_category TEXT NOT NULL, new_category TEXT NOT NULL,
      old_date TEXT NOT NULL,     new_date TEXT NOT NULL,
      old_description TEXT,       new_description TEXT,
      FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
  )
  ```
  - `update_expense()` records one row per successful edit, **in the same
    transaction** as the `UPDATE`: it reads the old values first (still
    scoped by `id = ? AND user_id = ?`), updates the expense, then inserts
    the old and new values. `expenses.updated_at` and `edited_at` get the
    same timestamp. A "No changes to save." submit writes nothing (FR16),
    so it adds no history.
  - Deleting an expense (Step 9) deletes its history too (`ON DELETE
    CASCADE`; `get_db()` already turns foreign keys on).
- **FR22 — History popup.** Clicking an edited badge opens
  `#edit-history-modal`, one shared popup built like the other popups
  (`.modal` + `.modal-overlay[data-modal-close]` + `.modal-content` with a
  `×` `.modal-close`, the same `.opening` animation). It's only rendered
  when at least one shown row has history. Top to bottom:
  1. Heading `h2` **Edit history**.
  2. The expense as it is now: `<date> · <category> · ₹<amount> ·
     <description or —>`.
  3. One entry per edit, **newest first**. Each entry shows when it
     happened (`D Mon YYYY, h:mm AM/PM`, converted from UTC to the
     computer's local time), then **only the fields that changed** in that
     edit, one line each, `<Field>: <old> → <new>`. The old value is struck
     through. Fields are labelled Amount (`₹` + `inr`), Category, Date
     (`YYYY-MM-DD`) and Description (`—` when empty), in that order.
  - Closes with ×, a click on the overlay, or a **Close** button.
- **FR23 — Where the data comes from.** `/profile` loads the history for
  just the rows it shows (at most 5), with one new query
  `get_expense_edits(user_id, expense_ids)` (it joins `expenses` so only
  the signed-in user's history is returned). Each edited row's entries
  are rendered server-side into a `<template id="edit-history-<id>">`. The
  JS copies that template into the popup, so there's no extra request
  and no `innerHTML` with user text (Jinja autoescapes it).
- **FR24 — JS.** A new IIFE in `static/js/main.js`
  (`// Profile: edit-history popup, opened from each row's edited badge`),
  starting with `if (!modal) return;`. It opens the popup with the matching
  template's content and closes it via `[data-modal-close]`.
- **FR25 — Edits made before history existed.** Rows edited before this
  table existed have an `updated_at` but no history. On startup,
  `init_db()` runs
  `UPDATE expenses SET updated_at = NULL WHERE updated_at IS NOT NULL AND
  id NOT IN (SELECT expense_id FROM expense_edits)`, so those rows lose
  their badge (and show "Never edited" on the edit page). The developer
  chose this over keeping a badge with no history behind it. After the
  first run it changes nothing, because every later edit writes history.

## 3. APIs

| Route | Method | Input | Output |
|---|---|---|---|
| `/expenses/<int:id>/edit` | GET | URL `id`. Query, all optional: `range`, `start`, `end` | Signed out: 302 → `/login` + error flash. Not found / not yours: 404. Else: 200, edit page |
| `/expenses/<int:id>/edit` | POST | URL `id`. Form: `amount`, `category`, `date` (`YYYY-MM-DD`), `description` (optional); optional `range`, `start`, `end` | Signed out: 302 → `/login`. Not found / not yours: 404. Invalid: 200 + error. No changes: 302 → `/profile?<filter>#expense-<id>` + `No changes to save.` Success: 302 → `/profile?<filter>#expense-<id>` + `Expense updated.` |
| `/expenses/<non-int>/edit` | any | — | 404 (Flask's `int` converter doesn't match) |

**DB helpers** (`database/db.py`, `?` placeholders, closed in `finally` like
`insert_expense`):

```python
def get_expense(user_id, expense_id)            # -> sqlite3.Row | None
def update_expense(user_id, expense_id, amount, category, date, description)  # -> bool; also writes expense_edits
def get_expense_edits(user_id, expense_ids)    # -> list of expense_edits rows, newest first
```

**Schema change:** `expenses.updated_at TEXT` (nullable, UTC
`YYYY-MM-DD HH:MM:SS`, set only by `update_expense`).

**Pencil link example:**
`/expenses/42/edit?range=custom&start=2026-09-01&end=2026-09-23`

## 4. Files and Interfaces Involved

| File | Change |
|---|---|
| `database/db.py` | `updated_at` in `CREATE TABLE expenses` + idempotent `ALTER TABLE` in `init_db()`; new `expense_edits` table + the FR25 cleanup; new `get_expense()`, `update_expense()` (writes history), `get_expense_edits()` |
| `app.py` | `profile()` passes each shown row's edit history (FR23), with a helper that turns an `expense_edits` row into its changed-field lines and a local-time formatter. `edit_expense(id)` route: stub → `GET`/`POST`, login check, 404, validation (share Step 7's parsing/validation with `add_expense` rather than copy it, e.g. a small helper in `app.py`), no-change check, update, flash, redirect. `add_expense` keeps the same behaviour |
| `templates/add_expense.html` | Made to serve both pages: title, subtitle, form action and submit label come from the route; the original-values line, edited-on line and filter hidden inputs render only on the edit page; Cancel link uses the filter on edit |
| `templates/profile.html` | Pencil `<a class="row-edit-btn">` before each trash button; edited badge button in the Date cell; `#edit-history-modal` + one `<template>` per edited row |
| `static/css/profile.css` | Wider Actions column, `.row-edit-btn`, Date-column gutter + `.edited-badge` (tokens only) |
| `static/css/add_expense.css` | Styles for the original-values and edited-on lines, if needed (tokens only) |
| `static/js/main.js` | New IIFE: on Back/Forward arrival at the edit page, `location.replace` to the profile row (FR20). New IIFE: edit-history popup (FR24) |
| `.claude/PROGRESS.md` | (At Git finish) route row `GET /expenses/<id>/edit — Stub — Step 8` → `GET/POST /expenses/<id>/edit — Implemented — Step 8` |

## 5. Constraints

- Flask + sqlite3 + vanilla JS only. No new packages. The only new
  JavaScript is the FR20 Back-arrow IIFE. Scrolling (FR19) uses a plain URL
  anchor.
- All SQL through `database/db.py` with `?` placeholders. The ownership check
  lives in the SQL `WHERE id = ? AND user_id = ?` of both helpers.
- `abort(404)` for not-found, not a returned string. The route renders a
  template (no raw string left behind).
- Internal links and form actions use `url_for`.
- The validation rules and messages must stay identical to Add expense. One
  shared implementation, so the two can't drift apart.
- The migration must be safe to run on every startup (idempotent) and must
  not change or lose existing rows.
- Colours and sizes through existing CSS custom properties. No new hex
  values.
- Jinja autoescaping stays on. Descriptions are user input.
- `app.run(debug=True, port=5001)` unchanged.

## 6. Out of Scope

- Editing from anywhere other than the Recent Transactions rows (a full
  expense list or Analytics page is a later feature). Any own expense id
  still opens via a typed URL.
- An edit popup/modal, inline editing in the table, or any JavaScript beyond
  FR20.
- The same Back-arrow behaviour for the Add expense page (Step 7). Not
  requested; it would need its own change.
- Undo, or restoring a previous version from the history popup (the popup
  is read-only).
- History for expenses not shown in Recent Transactions (no full list yet).
- Recovering history for edits made before the `expense_edits` table
  existed (FR25 clears their badge instead).
- Showing the full edited time (hours/minutes) or converting it to local
  time. The date part is shown as stored (UTC). See Edge Cases.
- Bulk edit.
- Changing who owns an expense.
- CSRF protection (a PROGRESS.md Open Task with its own spec).
- Changing Add expense's behaviour, or Delete's popup/animation.
- Visual polish beyond existing tokens and the Add expense page's look.

## 7. Edge Cases and Error Handling

| Case | Behaviour |
|---|---|
| Signed out, GET or POST | 302 → `/login`, flash `Please sign in to edit an expense.`, nothing written (FR8) |
| Id doesn't exist | 404 (FR9) |
| Id belongs to another user | 404; their row untouched (FR9, FR13) |
| Expense deleted in another tab, then Save | `get_expense` → `None` → 404 |
| Deleted between load and update (race) | `update_expense` returns `False` → 404 (FR17) |
| Invalid amount/category/date/description | Step 7's messages; 200 re-render keeping typed values; nothing written (FR14–15) |
| Save with nothing changed | No write, `updated_at` unchanged, toast `No changes to save.` (FR16) |
| Only whitespace added to the description | Treated as unchanged (stripped before comparing) |
| Amount `250` vs stored `250.0` | Treated as unchanged (compared as numbers after rounding) |
| Clearing the description | Stored as `NULL`; the row shows `—` and the edited badge |
| New date outside the current filter | Saved; the row isn't on the page it redirects to; the toast still shows (FR18) |
| Opened by typed URL with no filter args | Cancel and Save go to plain `/profile` |
| Bad `range`/`start`/`end` values | Passed through unchanged; `/profile`'s existing filter handling shows its own message |
| Old `database.db` without `updated_at` | Column added on startup; all old rows show `Never edited` and no badge |
| Delete an edited expense | Its `expense_edits` rows are deleted too (FR21) |
| An edit saved twice with the same values | The second is "No changes to save.", so it adds no history entry |
| History entry where only the description was cleared | One line: `Description: <old> → —` |
| `updated_at` is UTC | Between 00:00 and 05:30 IST the "Last edited" date shows the previous day. This is the same known UTC-vs-local issue already listed in PROGRESS.md; it's not fixed here |
| Description with HTML like `<b>x</b>` | Shown as literal text on the edit page and in the table (autoescape) |

## 8. Acceptance Criteria

- [ ] **AC1** — After app startup, `expenses` has an `updated_at` column, on a fresh DB and on an existing DB created before this step. Existing rows have `updated_at` = `NULL`, and their other values are unchanged.
- [ ] **AC2** — Signed in, with expenses in range, every Recent Transactions row has an `<a>` with `aria-label="Edit expense"` placed before the `Delete expense` button in the same cell.
- [ ] **AC3** — The pencil link's `href` is `/expenses/<id>/edit?range=<active range>`, and with a custom range it also has `start=` and `end=`.
- [ ] **AC4** — Signed in, `GET /expenses/<own id>/edit` returns **200** with the title **Edit expense**, the budget line, `Currently: <date> · <category> · ₹<amount> · <description or —>`, `Never edited` for a never-edited expense, the 4 fields pre-filled with the stored values, a **Save changes** button and a **Cancel** link.
- [ ] **AC5** — The edit form posts to `/expenses/<id>/edit` and carries the `range`/`start`/`end` from the page's query string as hidden inputs. Cancel's `href` is `/profile` with the same args plus `#expense-<id>`.
- [ ] **AC6** — Valid changed POST → **302**, `Location` `/profile?<the range/start/end sent>#expense-<id>`; the next page shows the toast **Expense updated.**; the DB row has the new amount/category/date/description and a non-NULL `updated_at`; that row has `class="row-new"` on the page it redirects to.
- [ ] **AC7** — After an edit, that row's Date cell starts with a `button.edited-badge` (dark pencil in a yellow circle), and never-edited rows have none. Hovering it shows the tooltip `Edited <D Mon YYYY, h:mm AM/PM> · click for history` immediately. Dates in all rows stay lined up, and the Description column shows as much text as before this step.
- [ ] **AC8** — After an edit, the edit page shows `Last edited <YYYY-MM-DD>` in place of `Never edited`.
- [ ] **AC9** — POST with values identical to the stored ones → **302** to `/profile?<filter>#expense-<id>`, toast **No changes to save.**, and `updated_at` unchanged (still `NULL` if never edited).
- [ ] **AC10** — Each of the 7 invalid inputs returns **200** with its exact Step 7 message, keeps the typed values, and leaves the DB row unchanged.
- [ ] **AC11** — Signed out, GET and POST `/expenses/<id>/edit` both return **302** to `/login` with the flash **Please sign in to edit an expense.**, and nothing changes in the DB.
- [ ] **AC12** — Signed in, GET and POST to an id that doesn't exist return **404**.
- [ ] **AC13** — Signed in as user A, GET and POST to user B's expense id return **404**, and user B's row is unchanged.
- [ ] **AC14** — After an edit, Total Spent / Transactions / By Category reflect the new amount/category.
- [ ] **AC15** — `/expenses/add` still shows **Add an expense**, button **Add expense**, posts to `/expenses/add`, and shows no `Currently:` / `Never edited` lines. Adding an expense still works as in Step 7.
- [ ] **AC16** — A description `<b>x</b>` shows as literal text in the `Currently:` line and in the table.
- [ ] **AC17** — Every Recent Transactions row has `id="expense-<id>"`. After a successful save (or a no-changes save), the redirect `Location` ends with `#expense-<id>`, and the browser shows that row in view, below the navbar.
- [ ] **AC19** — Each successful edit adds exactly one `expense_edits` row with the old and new values and `edited_at` equal to the expense's `updated_at`. A "No changes to save." submit adds none.
- [ ] **AC20** — Clicking an edited badge opens **Edit history** showing that expense's current values and one entry per edit, newest first, each listing only the changed fields as `<Field>: <old> → <new>`, with the old value struck through. ×, the overlay and **Close** each close it.
- [ ] **AC21** — Deleting an edited expense also deletes its `expense_edits` rows.
- [ ] **AC22** — After startup, no expense has `updated_at` set without at least one `expense_edits` row (FR25), and those rows show no badge.
- [ ] **AC23** — A description like `<b>x</b>` in a history entry shows as literal text.
- [ ] **AC18** — After saving an edit, pressing the browser's Back arrow shows `/profile` (with the same filter, scrolled to that row), not the edit form. The same happens after Cancel → Back. Clicking a pencil normally still opens the edit page.

## 9. Manual Verification Guide

**Setup (do once).** In a terminal, from the `expense-tracker` folder:

```bash
source venv/bin/activate
python app.py
```

Leave it running. It runs `init_db()` on startup, which adds the new column
to your existing `database.db`. Open **http://localhost:5001** in Chrome and
register a test account at **http://localhost:5001/register**, e.g.
`Step Eight` / `step8@example.com` / `testpass1`. Then add **two** expenses
through **Add expense** in the navbar, both dated today:

| Amount | Category | Description |
|---|---|---|
| 250 | Food | `Lunch` |
| 40 | Other | `<b>x</b>` |

Keep a **second terminal** open in the same folder for the read-only
`sqlite3` checks below. To find your expense ids:

```bash
sqlite3 database.db "SELECT id, amount, category, date, description, updated_at FROM expenses WHERE user_id = (SELECT id FROM users WHERE email='step8@example.com');"
```

Expected: two lines like `61|250.0|Food|2026-09-23|Lunch|` and
`62|40.0|Other|2026-09-23|<b>x</b>|`. The empty last field is
`updated_at` = NULL. Your ids will differ; write them down.

---

**AC1 — new column exists.**
1. Second terminal: `sqlite3 database.db "PRAGMA table_info(expenses);"`
2. Expected: the last line ends in `updated_at|TEXT|0||0`.
3. `sqlite3 database.db "SELECT COUNT(*) FROM expenses WHERE updated_at IS NOT NULL;"` → `0` before you edit anything.

**AC2 — pencil on every row.**
1. Go to **http://localhost:5001/profile**.
2. Expected: each Recent Transactions row has two small icons on the right, a pencil and then a trash can.
3. Right-click the pencil → **Inspect**: it's an `<a class="row-edit-btn" aria-label="Edit expense" ...>`, and the next element is the trash `<button>`.

**AC3 — pencil link keeps the filter.**
1. On `/profile`, hover the **Lunch** row's pencil and look at the bottom-left of Chrome: `…/expenses/61/edit?range=this_month`.
2. Click the **Last 3 months** pill, hover again: `?range=last_3_months`.
3. Pick a custom From/To range, apply, hover: the link has `range=custom&start=…&end=…`.

**AC4 — edit page content.**
1. Go back to the default filter and click the **Lunch** row's pencil.
2. Expected, top to bottom: **Edit expense**, the subtitle, the budget line (e.g. `No monthly budget set`), `Currently: 2026-09-23 · Food · ₹250.00 · Lunch`, `Never edited`, then the form with Amount `250.0`, Category **Food**, Date today and Description `Lunch`, a **Save changes** button and **Cancel**.

**AC5 — form target and filter carry.**
1. On the edit page, right-click → **Inspect**, press **Cmd+F** and search `<form`.
2. Expected: `action="/expenses/61/edit"`. Inside it there's `<input type="hidden" name="range" value="this_month">`.
3. Hover **Cancel**: the link is `/profile?range=this_month#expense-61`.

**AC6 — successful edit.**
1. Change Amount to `300`, Category to **Transport** and Description to `Cab`, then click **Save changes**.
2. Expected: back on `/profile?range=this_month#expense-61`, toast **Expense updated.**, and the row now reads `Cab · Transport · ₹300.00` with a brief green highlight.
3. Second terminal: re-run the Setup query. The Lunch line is now like `61|300.0|Transport|2026-09-23|Cab|2026-09-23 10:15:02`, and `updated_at` is filled in.
4. The 302: DevTools → **Network** → tick **Preserve log** → edit again (e.g. amount `310`) → click the request named `edit` → **Status Code: 302 FOUND**, `Location: /profile?range=this_month#expense-61`.

**AC7 — edited badge.**
1. On `/profile`: the Cab row has a small yellow circle with a dark pencil inside, just left of its date. It looks clearly different from the plain pencil edit button on the right. The `<b>x</b>` row has none, and both dates line up in the same column.
2. Move the mouse onto the yellow circle: a small dark tooltip appears **straight away** reading `Edited 23 Sep 2026, 3:45 PM · click for history` (your time).
3. Give the Cab row a long description (e.g. `Sample Entertainment expense for the whole team outing`) and save. Expected: the badge is still fully visible by the date. The description gets cut off with `…` as usual.

**AC8 — last edited date.**
1. Click the Cab row's pencil. Expected: `Last edited 2026-09-23` in place of `Never edited`. (Between 00:00 and 05:30 IST it may show yesterday's date. That's the known UTC issue from §7.)

**AC9 — no changes.**
1. In the second terminal, note the Cab row's `updated_at`.
2. On its edit page click **Save changes** without changing anything.
3. Expected: back on `/profile`, toast **No changes to save.**, no green highlight.
4. Re-run the Setup query: `updated_at` is exactly the same as before.
5. Repeat on the `<b>x</b>` row: after saving, its `updated_at` is still empty and it has no edited badge.

**AC10 — validation.** On the Cab row's edit page, try each of these and click **Save changes**. Each shows the red message above the form, keeps what you typed, and changes nothing in the DB (re-run the Setup query after):

| Change | Expected message |
|---|---|
| Clear Amount | `Please enter an amount.` |
| Amount `0` | `Amount must be a number greater than 0.` |
| Amount `20000000` | `Amount can't be more than ₹1,00,00,000.00.` |
| DevTools: edit the `<option>` value to `Pets`, pick it | `Please choose a category.` |
| DevTools: remove `required` from Date, clear it | `Please enter a valid date.` |
| DevTools: remove `max` from Date, pick tomorrow | `Date can't be in the future.` |
| DevTools: remove `maxlength`, paste 201 characters | `Description must be 200 characters or fewer.` |

(To edit an attribute: right-click the field → **Inspect**, double-click the attribute in the Elements panel, delete it and press Enter.)

**AC11 — signed out.**
1. Click **Sign out**. Visit **http://localhost:5001/expenses/61/edit**.
2. Expected: you land on the login page with **Please sign in to edit an expense.**
3. Second terminal: `curl -i -X POST -d "amount=1&category=Food&date=2026-09-01" http://localhost:5001/expenses/61/edit` → first line `HTTP/1.1 302 FOUND`, with `Location: /login`. Re-run the Setup query: the row is unchanged.

**AC12 — id that doesn't exist.**
1. Sign back in and visit **http://localhost:5001/expenses/999999/edit** → a **Not Found** page.

**AC13 — someone else's expense.**
1. `sqlite3 database.db "SELECT id FROM expenses WHERE user_id != (SELECT id FROM users WHERE email='step8@example.com') LIMIT 1;"`. Note the id (e.g. `12`). If it prints nothing, register a second account, add one expense there, and run it again.
2. As `step8@example.com`, visit `/expenses/12/edit` → **Not Found**.
3. In DevTools **Console** on `/profile`: `fetch('/expenses/12/edit', {method:'POST', body:new URLSearchParams({amount:'1',category:'Food',date:'2026-09-01'})}).then(r => console.log(r.status))` → `404`.
4. `sqlite3 database.db "SELECT amount, updated_at FROM expenses WHERE id = 12;"` → unchanged.

**AC14 — figures update.**
1. Note Total Spent and the By Category bars. Edit Cab's amount from `310` to `100`.
2. Expected: Total Spent drops by ₹210.00, and the Transport bar shrinks to match.

**AC15 — Add expense unchanged.**
1. Click **Add expense** in the navbar. Expected: the title **Add an expense**, a button **Add expense**, empty fields, today's date, and no `Currently:` or `Never edited` line.
2. Add `5`, Other, `add-check`. Expected: as in Step 7, back on `/profile` with toast **Expense added.** and the row highlighted.

**AC16 — HTML shown as text.**
1. Click the `<b>x</b>` row's pencil. Expected: the `Currently:` line shows the characters `<b>x</b>`, not a bold **x**. Same in the table on `/profile`.

**AC17 — scrolls to the edited row.**
1. Make the browser window short (drag its bottom edge up) so the Recent Transactions card is below the fold when `/profile` loads.
2. Click the Cab row's pencil, change the amount, click **Save changes**.
3. Expected: `/profile` opens already scrolled down, with the Cab row visible *below* the navbar (not hidden under it) and flashing green. The address bar ends in `#expense-61`.
4. Right-click the row → **Inspect**: the `<tr>` has `id="expense-61"`.

**AC19 — one history row per edit.**
1. Second terminal: `sqlite3 database.db "SELECT expense_id, edited_at, old_amount, new_amount, old_category, new_category FROM expense_edits WHERE expense_id = 61;"`
2. Expected: one line per real edit you made to Cab, e.g. `61|2026-09-23 10:15:02|250.0|300.0|Food|Transport`. Its `edited_at` matches the Cab row's `updated_at` from the Setup query.
3. Save the Cab edit page once with no changes, then re-run step 1: still the same number of lines.

**AC20 — history popup.**
1. On `/profile`, click the Cab row's yellow badge.
2. Expected: a popup **Edit history**, the Cab row's current values, then the edits newest first. Your first edit reads something like `Amount: ~~₹250.00~~ → ₹300.00`, `Category: ~~Food~~ → Transport`, `Description: ~~Lunch~~ → Cab`. A later amount-only edit shows just the Amount line.
3. Close it with ×, then reopen and click outside the box, then reopen and click **Close**. Each one closes it.

**AC21 — delete removes history.**
1. Edit the `<b>x</b>` row once (amount `41`), then delete it with its trash icon.
2. `sqlite3 database.db "SELECT COUNT(*) FROM expense_edits WHERE expense_id = 62;"` → `0`.

**AC22 — old badges without history cleared.**
1. `sqlite3 database.db "SELECT COUNT(*) FROM expenses WHERE updated_at IS NOT NULL AND id NOT IN (SELECT expense_id FROM expense_edits);"` → `0`.
2. Rows edited before this change (e.g. the sample rows 40, 41, 43) show no badge, and their edit page says `Never edited`.

**AC23 — HTML in history shown as text.** *(do this before AC21)*
1. Change the `<b>x</b>` row's description to `plain`, save, and click its badge.
2. Expected: `Description: <b>x</b> → plain`, with `<b>x</b>` shown as characters, not bold.

**AC18 — Back arrow skips the old edit form.**
1. On `/profile`, click the Cab row's pencil, change the amount, click **Save changes**.
2. Click the browser's **Back** arrow (←) once.
3. Expected: you're on `/profile` (address bar `/profile?range=this_month#expense-61`), scrolled to the Cab row, showing the *new* amount. You don't see the edit form.
4. Repeat, but click **Cancel** on the edit page instead of saving, then **Back**: same result.
5. Click the pencil normally: the edit page opens as usual (it isn't redirected away).

**Cleanup.** The `step8@example.com` account and its expenses are yours to
keep or delete with the trash buttons.

## 10. End-to-End Verification

Run the spec's tests once `/test-feature` has written them:

```bash
venv/bin/python -m pytest tests/test_08-edit-button-feature.py -v
```

Expected: all tests pass. At minimum the file covers these, using
`auth_client` from `tests/conftest.py` and `db.insert_expense` for setup, on
the throwaway test DB, never `database.db`:

1. Insert an expense → `GET /expenses/<id>/edit` → 200, contains
   `Edit expense`, `Never edited`, `Save changes`, the stored values.
2. `POST` changed values with `range=last_3_months` → 302, `Location` ends
   with `/profile?range=last_3_months#expense-<id>`; following it shows `Expense updated.`,
   `edited-badge`, and `row-new`; DB row updated, `updated_at` not NULL.
3. `POST` identical values → 302, `No changes to save.`, `updated_at`
   unchanged.
4. Each of the 7 invalid inputs → 200 + exact message, DB unchanged.
5. Signed out GET/POST → 302 `/login`; missing id → 404; other user's id → 404, row unchanged.
6. `/profile` with an expense contains `aria-label="Edit expense"`,
   `href="/expenses/<id>/edit?range=this_month"` and `id="expense-<id>"`.
   The edit page contains `id="edit-expense-form"` and
   `data-back-to="/profile?range=this_month#expense-<id>"` when opened with
   `?range=this_month`. (The Back-arrow redirect itself is browser behaviour,
   so AC18 is checked by hand.)
7. `/expenses/add` still shows `Add an expense` and no `Never edited`.
7b. Two edits of one expense → two `expense_edits` rows with the right old/new
    values; `/profile` contains `class="edited-badge"`,
    `id="edit-history-modal"` and `<template id="edit-history-<id>">` with
    `Amount`; a no-changes save adds no row; deleting the expense removes its
    rows; `init_db()` clears `updated_at` on a row with no history.
8. `init_db()` on a DB created with the old `expenses` schema (without
   `updated_at`) adds the column and keeps existing rows.

Then the full suite as a regression check:

```bash
venv/bin/python -m pytest
```

Expected: no new failures compared with `main`. The known UTC-vs-local
`test_showing_line_for_fresh_user_starts_at_signup_date` failure between
00:00 and 05:30 IST is a pre-existing Open Task, not caused by this step.

