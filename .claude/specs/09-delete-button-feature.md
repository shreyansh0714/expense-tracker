# Spec 09 — Delete expense (button + confirm popup)

**Status:** Draft — not yet implemented
**Branch:** `feature/delete-button-feature` (branched off `main` at `86f9f09`,
after the Step 7 merge, PR #11)
**Date:** 2026-09-22

**Order note:** Step 8 (Edit expense) has no spec yet. The developer chose
to build Step 9 first. Nothing here depends on Step 8. The new actions
column holds only the delete button, and Step 8 adds its edit button next
to it later.

**Design reference:** none. No mockup exists for this feature (confirmed in
the interview). It reuses the existing `.modal` popup pattern and the
Feather-style icon macros in `templates/_icons.html`. Any later visual
polish must not add, remove or reword the content listed here (see
CLAUDE.md, "Mockup content convention").

---

## 1. Problem Statement

Since Step 7 a user can add expenses, but there's no way to remove one. A
typo'd amount, a duplicate, or a test entry stays in the totals, the
stat tiles and the By Category card forever. `/expenses/<id>/delete` is a
stub in `app.py` that returns the plain string
`"Delete expense — coming in Step 9"`, only accepts GET, and nothing links
to it.

This step makes deleting an expense a real feature:

1. A trash button on every row of the **Recent Transactions** table on
   `/profile`.
2. A confirmation popup that shows exactly which expense is about to go
   (date, description, category, amount), with **Cancel** and **Delete**.
3. On **Delete**: the row flashes red and fades out, then the expense is
   removed from the database.
4. The user lands back on `/profile` with the **same date filter** they
   were viewing and an "Expense deleted." toast. Totals, stat tiles and
   By Category all reflect the removal.

## 2. Functional Requirements

### The button — `/profile` Recent Transactions table

- **FR1 — Actions column.** The Recent Transactions table
  (`table.transactions-table` in `templates/profile.html`) gets a 5th,
  last column. Its `<th>` is empty (no visible text); each button in it
  carries its own `aria-label` (FR2).
- **FR2 — Trash button per row.** Every row (at most 5, the rows already
  shown for the chosen date range) gets one
  `<button type="button" class="row-delete-btn">` in that column:
  - Content: a new `icons.trash()` macro from `templates/_icons.html`
    (Feather "trash-2" glyph, same `_svg()` helper and default size 16 as
    `icons.edit()`). No visible text.
  - `aria-label="Delete expense"`.
  - Carries the data the popup needs as `data-*` attributes:
    `data-action` = `url_for('delete_expense', id=expense.id)`,
    `data-date` = `expense.date` (same text the Date cell shows),
    `data-description` = `expense.description or "—"`,
    `data-category` = `expense.category`,
    `data-amount` = `"₹" ~ expense.amount|inr` (same text the Amount
    cell shows).
- **FR3 — Nothing else changes on the page.** Other cards, the "+ Add
  expense" and "View all" links, and both empty-state messages stay
  exactly as they are.

### The popup — `#delete-expense-modal`

- **FR4 — One shared popup.** `templates/profile.html` gets one popup,
  `<div class="modal" id="delete-expense-modal" hidden>`, using the same
  structure as the existing edit-profile popup: a
  `div.modal-overlay` with `data-modal-close`, then a `div.modal-content`
  holding a `button.modal-close` (`&times;`, `data-modal-close`).
  It's only rendered when `recent_expenses` is non-empty. It opens with
  the same `crumple-open` animation as the edit-profile popup (the
  existing `.opening` class), which is already skipped under
  `prefers-reduced-motion: reduce`.
- **FR5 — Popup content (read-only), top to bottom:**
  1. Heading `h2`: **Delete this expense?**
  2. A details list showing the clicked row's values, labelled
     **Date**, **Description**, **Category**, **Amount**. The values are
     filled in by JS from the button's `data-*` attributes (FR2), using
     `textContent`, never `innerHTML`.
  3. A line: **This can't be undone.**
  4. A form, `method="post"`, whose `action` JS sets to the clicked
     button's `data-action`. It holds:
     - hidden inputs `range`, `start`, `end`, carrying the page's current
       filter values the same way the budget form does (only the ones
       that are set);
     - a **Cancel** button (`type="button"`, `data-modal-close`);
     - a **Delete** submit button (`type="submit"`, class
       `btn-danger`, new in `style.css`: `--danger` background,
       `--paper-card` text, otherwise shaped like the existing `btn-submit`).
- **FR6 — Closing without deleting.** Cancel, the × button, and a click
  on the overlay all close the popup (existing `[data-modal-close]`
  behaviour). Nothing is sent to the server and the row stays. Escape
  isn't handled: none of the existing popups support it, and adding it
  is out of scope.

### The animation — `static/js/main.js` + `static/css/profile.css`

- **FR7 — Animate, then save.** When **Delete** is clicked in the popup:
  1. JS stops the normal submit (`preventDefault`) and disables the
     Delete button so a double-click can't send two POSTs.
  2. The popup closes.
  3. The row whose button opened the popup gets class `row-deleting`.
     It turns `--danger-light` with `--danger` text, then fades to
     transparent, over about **0.6 s** in total. The row does not
     collapse (shrink in height); the gap lasts only until the reload.
  4. When the animation ends (`animationend`), JS calls `form.submit()`.
     A fallback timer (≈ 1 s) also calls `form.submit()` in case
     `animationend` never fires. Submitting runs only once.
- **FR8 — Reduced motion.** When
  `window.matchMedia('(prefers-reduced-motion: reduce)').matches`, there's
  no animation: the popup closes and the form submits straight away. The
  `.row-deleting` CSS is also wrapped so it doesn't animate under
  `prefers-reduced-motion: reduce`.
- **FR9 — JS structure.** A new IIFE block in `main.js`, named in a
  comment like the others (e.g. `// Delete expense popup`). It starts with
  `if (!modal) return;` so pages without the popup are unaffected.

### Deleting — `POST /expenses/<int:id>/delete`

- **FR10 — POST only.** The existing stub route
  `@app.route("/expenses/<int:id>/delete")` becomes
  `methods=["POST"]`. A GET gets Flask's automatic **405 Method Not
  Allowed**.
- **FR11 — Login required.** No `user_id` in the session → flash
  `Please sign in to delete an expense.` (category `error`) and redirect
  to `url_for('login')`. Nothing is deleted.
- **FR12 — Own expenses only.** The route calls a new
  `delete_expense(user_id, expense_id)` in `database/db.py`, passing
  `session["user_id"]`. The query is
  `DELETE FROM expenses WHERE id = ? AND user_id = ?`, and it returns
  `True` if exactly one row was deleted, otherwise `False`.
- **FR13 — Not found.** If `delete_expense` returns `False` (the id
  doesn't exist, was already deleted, or belongs to another user), the
  route calls `abort(404)`. The same 404 in all three cases, so a user
  can't tell whether someone else's expense id exists.
- **FR14 — Success.** On `True`: flash `Expense deleted.` (category
  `success`) and redirect to `url_for('profile', **filter_args)`, where
  `filter_args` is built from the form's `range`/`start`/`end` exactly as
  `save_budget()` does (only non-empty keys).

### After deleting — `/profile`

- **FR15 — Page reflects the removal.** The deleted row is gone from
  Recent Transactions. Total Spent, Transactions and Top Category tiles,
  By Category, the range+budget bar and the month-by-month budget table
  all reflect it (they already query the DB on every load, so nothing
  new is needed). If another expense in the range existed beyond the 5
  shown, it now moves up into view.
- **FR16 — Last expense.** Deleting the user's only expense shows the
  existing **You haven't logged any expenses yet.** empty state (with its
  **Add your first expense** link). Deleting the last expense in the
  current range, when others exist outside it, shows the existing
  **No expenses between … Try a wider range.** message.

## 3. APIs

| Route | Method | Input | Output |
|---|---|---|---|
| `/expenses/<int:id>/delete` | POST | URL: `id` (int). Form, all optional: `range`, `start`, `end` (strings, passed through untouched) | Signed out: 302 → `/login` + error flash. Not found / not yours: 404. Success: 302 → `/profile?<filter args>` + success flash `Expense deleted.` |
| `/expenses/<int:id>/delete` | GET | — | 405 Method Not Allowed |
| `/expenses/<non-int>/delete` | any | — | 404 (Flask's `int` converter doesn't match) |

**New DB helper** (`database/db.py`):

```python
def delete_expense(user_id, expense_id) -> bool
```

Opens a connection with `get_db()`, runs
`DELETE FROM expenses WHERE id = ? AND user_id = ?` with
`(expense_id, user_id)`, commits, closes in `finally` (same shape as
`insert_expense`), and returns `cur.rowcount == 1`.

**Row → popup data shape** (`data-*` on each trash button, strings):

| Attribute | Example |
|---|---|
| `data-action` | `/expenses/42/delete` |
| `data-date` | `2026-09-22` |
| `data-description` | `Groceries` (or `—` when empty) |
| `data-category` | `Food` |
| `data-amount` | `₹1,250.00` |

## 4. Files and Interfaces Involved

| File | Change |
|---|---|
| `app.py` | `delete_expense(id)` route: stub → POST-only, login check, calls `db.delete_expense`, `abort(404)` or flash + redirect. Imports `delete_expense` from `database.db` (name clash with the route function: import it as `from database.db import delete_expense as db_delete_expense`, or rename the route function; the endpoint name used by `url_for` must stay `delete_expense`) |
| `database/db.py` | New `delete_expense(user_id, expense_id)` |
| `templates/_icons.html` | New `trash(size=16)` macro |
| `templates/profile.html` | Actions `<th>` + per-row trash button; the shared `#delete-expense-modal` popup |
| `static/js/main.js` | New IIFE: open/fill popup, animate row, submit once |
| `static/css/profile.css` | Actions column + `.row-delete-btn` styles, `.row-deleting` keyframes, reduced-motion guard. Tokens only (`--danger`, `--danger-light`, `--ink`, etc.) |
| `static/css/style.css` | New shared `.btn-danger` (none exists yet) |
| `.claude/PROGRESS.md` | (At Git finish) route row `GET /expenses/<id>/delete — Stub` → `POST /expenses/<id>/delete — Implemented — Step 9` |

## 5. Constraints

- Flask + sqlite3 + vanilla JS only. No new packages, no `confirm()`
  dialog, no JS framework.
- All SQL through `database/db.py` with `?` placeholders.
- The ownership check lives in the SQL `WHERE ... AND user_id = ?`, not
  in a separate "load then compare" step.
- `abort()` for the 404, not a returned string.
- Internal links and form actions use `url_for`. The popup's form action
  comes from `data-action`, which is itself built with `url_for`.
- Popup values set with `textContent`, never `innerHTML` (descriptions
  are user input).
- Colours and sizes through existing CSS custom properties. No new hex
  values.
- The animation must respect `prefers-reduced-motion` (FR8).
- `app.run(debug=True, port=5001)` unchanged.

## 6. Out of Scope

- Editing an expense (Step 8). No edit button or placeholder in the
  actions column.
- Undo, soft delete, or a trash/restore area.
- Bulk delete / selecting several rows.
- Deleting from anywhere other than the Recent Transactions rows on
  `/profile` (e.g. a full expense list or the Analytics page, which are
  later features). Older expenses are reached by changing the date
  filter.
- A no-JavaScript fallback. With JS disabled the trash button does
  nothing (see Edge Cases).
- CSRF protection (tracked in PROGRESS.md Open Tasks as its own spec).
- Changing the Step 7 green new-row highlight.
- Closing popups with the Escape key (no existing popup supports it).
- Visual polish beyond existing tokens and the existing modal look.

## 7. Edge Cases and Error Handling

| Case | Behaviour |
|---|---|
| Signed out, POST | 302 → `/login`, flash `Please sign in to delete an expense.`, nothing deleted (FR11) |
| GET to the delete URL (typed in the address bar, old bookmark) | 405, nothing deleted (FR10) |
| Id doesn't exist | 404 (FR13) |
| Id belongs to another user | 404, their row untouched (FR13) |
| Same expense deleted twice (two tabs, or a resent form) | First: success. Second: 404 |
| Double-click on Delete in the popup | Button disabled after the first click, one POST only (FR7) |
| `animationend` never fires | Fallback timer submits anyway (FR7) |
| Reduced motion | No animation, immediate submit (FR8) |
| Deleted row was the Step 7 highlighted new row | Nothing special: `new_expense_id` is already popped from the session on the load that showed it |
| Last expense overall / in range | Existing empty states (FR16) |
| Invalid `range`/`start`/`end` values in the form | Passed through unchanged. `/profile`'s existing filter handling shows its own error message, as it already does for bad query strings |
| Description contains HTML like `<b>x</b>` | Shown as literal text in the popup (`textContent`), not rendered |
| JavaScript disabled | Trash button does nothing, nothing deleted. Accepted limitation (Out of Scope) |

## 8. Acceptance Criteria

- [ ] **AC1** — Signed in with at least one expense in range, every row of the Recent Transactions table on `/profile` has a button with `aria-label="Delete expense"` in a 5th, last column.
- [ ] **AC2** — Each such button has `data-action="/expenses/<that row's id>/delete"` and `data-date`, `data-description`, `data-category`, `data-amount` matching the row's cells (`data-description` is `—` when the description is empty).
- [ ] **AC3** — `/profile` contains exactly one `#delete-expense-modal` (rendered `hidden`) when there are rows, with the heading **Delete this expense?**, the line **This can't be undone.**, a `method="post"` form, a **Cancel** button and a **Delete** submit button. When Recent Transactions is empty, the popup isn't rendered.
- [ ] **AC4** — Clicking a row's trash button opens the popup showing that row's Date, Description, Category and Amount.
- [ ] **AC5** — Cancel, × and clicking the overlay each close the popup, and the expense is still in the database and on the page.
- [ ] **AC6** — Clicking **Delete**: the popup closes, the row turns red and fades out (≈ 0.6 s), then the page reloads.
- [ ] **AC7** — With reduced motion turned on, clicking **Delete** reloads the page without the red fade.
- [ ] **AC8** — Signed in, `POST /expenses/<own id>/delete` returns **302** with `Location` `/profile?<the range/start/end sent>` (deleting from a plain `/profile` gives `/profile?range=this_month`, because the popup always sends the current `range`, the same as the budget form), the next page shows the toast **Expense deleted.**, and the row no longer exists in the `expenses` table.
- [ ] **AC9** — Filter kept: deleting while viewing e.g. `/profile?range=last_3_months` lands on `/profile?range=last_3_months`; with a custom range, `start` and `end` are both kept.
- [ ] **AC10** — After a delete, the Total Spent, Transactions and By Category figures drop by that expense.
- [ ] **AC11** — Signed out, `POST /expenses/<id>/delete` returns **302** to `/login`, flashes **Please sign in to delete an expense.**, and deletes nothing.
- [ ] **AC12** — `GET /expenses/<id>/delete` returns **405**, and deletes nothing.
- [ ] **AC13** — Signed in, `POST /expenses/<id that doesn't exist>/delete` returns **404**.
- [ ] **AC14** — Signed in as user A, `POST /expenses/<user B's expense id>/delete` returns **404**, and user B's expense is still in the table.
- [ ] **AC15** — Deleting the same id a second time returns **404**.
- [ ] **AC16** — Deleting a user's only expense shows **You haven't logged any expenses yet.** on `/profile`.
- [ ] **AC17** — A description containing `<b>x</b>` shows in the popup as the literal text `<b>x</b>`, not bold.

## 9. Manual Verification Guide

**Setup (do once).** In a terminal, from the `expense-tracker` folder:

```bash
source venv/bin/activate
python app.py
```

Leave it running. Open **http://localhost:5001** in Chrome. Register a fresh
test account at **http://localhost:5001/register**, e.g. `Step Nine` /
`step9@example.com` / `testpass1`. Then add **three** expenses through
**Add expense** in the navbar, all dated today:

| Amount | Category | Description |
|---|---|---|
| 100 | Food | `Tea` |
| 250 | Transport | *(leave empty)* |
| 40 | Other | `<b>x</b>` |

Keep a **second terminal** open in the same folder for the `sqlite3`
checks below. They only read and don't change anything.

To find your expense ids, run:

```bash
sqlite3 database.db "SELECT id, amount, description FROM expenses WHERE user_id = (SELECT id FROM users WHERE email='step9@example.com');"
```

Expected: three lines like `57|100.0|Tea`, `58|250.0|`, `59|40.0|<b>x</b>`.
Your numbers will differ; write them down.

---

**AC1 — trash button on every row.**
1. Go to **http://localhost:5001/profile**.
2. Expected: the Recent Transactions table has a 5th column on the right, with a small trash-can icon on each of the 3 rows.
3. Right-click one trash icon → **Inspect**. In the Elements panel the highlighted `<button>` has `aria-label="Delete expense"`.

**AC2 — the button's data.**
1. In the same Elements panel, look at the `<button>` tag for the **Tea** row.
2. Expected: `data-action="/expenses/57/delete"` (your Tea id), `data-date="<today, e.g. 2026-09-22>"`, `data-description="Tea"`, `data-category="Food"`, `data-amount="₹100.00"`.
3. On the **Transport** row's button: `data-description="—"`.

**AC3 — the popup markup.**
1. In the Elements panel press **Cmd+F** and search `delete-expense-modal`.
2. Expected: exactly one match, a `<div class="modal" id="delete-expense-modal" hidden>`. Expand it: you see **Delete this expense?**, **This can't be undone.**, a `<form method="post">`, a **Cancel** button and a **Delete** button.
3. Later, after AC16 (no expenses left), repeat the search: **0 matches**.

**AC4 — popup shows the clicked row.**
1. Click the trash icon on the **Tea** row.
2. Expected: a popup over a blurred page reading **Delete this expense?**, with Date = today, Description = `Tea`, Category = `Food`, Amount = `₹100.00`, and **This can't be undone.**
3. Close it (Cancel), click the **Transport** row's trash icon: now it shows Description `—`, Category `Transport`, Amount `₹250.00`.

**AC5 — closing without deleting.**
1. Open the popup on any row. Click **Cancel**: the popup closes and the row is still there.
2. Open it again, click the **×** in the corner: same.
3. Open it again, click the blurred area outside the white box: same.
4. In the second terminal re-run the id query from Setup: still three lines.

**AC6 — the red fade.**
1. Click the **Tea** row's trash icon, then **Delete**.
2. Expected: the popup closes, the Tea row turns light red with red text, fades away over about half a second, then the page reloads.
3. (Covered next by AC8: the toast and the row being gone.)

**AC7 — reduced motion.**
1. Open DevTools (**Cmd+Option+I**) → press **Cmd+Shift+P** → type `reduced motion` → pick **Emulate CSS prefers-reduced-motion: reduce**.
2. Add a throwaway expense (`5`, Other, `rm-test`), return to `/profile`, delete it with its trash icon → **Delete**.
3. Expected: the page reloads right away with no red fade.
4. Turn it back off: **Cmd+Shift+P** → **Emulate CSS prefers-reduced-motion: no-preference**.

**AC8 — successful delete (toast + DB).**
1. Right after AC6's reload, expected: a toast reading **Expense deleted.**, and the Tea row is gone.
2. Second terminal:
   ```bash
   sqlite3 database.db "SELECT COUNT(*) FROM expenses WHERE id = 57;"
   ```
   (your Tea id). Expected: `0`.
3. The 302 status: DevTools → **Network** tab → tick **Preserve log** → delete another throwaway expense → click the request named `delete` in the list. Expected: **Status Code: 302 FOUND**, and under Response Headers `Location: /profile?range=this_month` (the filter you were on; `this_month` when you hadn't picked one).

**AC9 — filter kept.**
1. Add a throwaway expense (`5`, Other, `filter-test`). On `/profile`, click **Last 3 months** in the filter bar. The address bar shows `/profile?range=last_3_months`.
2. Delete `filter-test` via its trash icon.
3. Expected: after the reload the address bar still shows the same `?range=…`, and **Last 3 months** is still the highlighted pill.
4. Repeat with a custom From/To range (pick today in both boxes, apply, add and delete a throwaway): the address bar keeps both `start=` and `end=`.

**AC10 — figures update.**
1. Before a delete, note **Total Spent**, **Transactions**, and the **Transport** bar in By Category.
2. Delete the `₹250.00` Transport row.
3. Expected: Total Spent drops by ₹250.00, Transactions drops by 1, and Transport disappears from By Category (it was the only one).

**AC11 — signed-out POST.**
1. Click **Sign out**.
2. Second terminal (use your `<b>x</b>` id):
   ```bash
   curl -i -X POST http://localhost:5001/expenses/59/delete
   ```
3. Expected: first line `HTTP/1.1 302 FOUND`, and a line `Location: /login`.
4. Re-run the id query from Setup: the `<b>x</b>` row is still there.
5. For the message: in Chrome, while signed out, you can't click a trash icon (profile needs sign-in), so the toast is checked by `/test-feature` instead. The curl status and the unchanged row are the manual check.

**AC12 — GET is refused.**
1. Sign back in. Type **http://localhost:5001/expenses/59/delete** in the address bar, press Enter.
2. Expected: a page saying **Method Not Allowed**.
3. Or in the terminal: `curl -i http://localhost:5001/expenses/59/delete` → first line `HTTP/1.1 405 METHOD NOT ALLOWED`.
4. Re-run the id query: the row is still there.

**AC13 — id that doesn't exist.**
1. Signed in, on `/profile`, open DevTools → **Console** tab and paste:
   ```js
   fetch('/expenses/999999/delete', {method: 'POST'}).then(r => console.log(r.status))
   ```
2. Expected: the console prints `404`.

**AC14 — someone else's expense.**
1. Find an expense that belongs to a *different* user:
   ```bash
   sqlite3 database.db "SELECT id, user_id FROM expenses WHERE user_id != (SELECT id FROM users WHERE email='step9@example.com') LIMIT 1;"
   ```
   Note the id (e.g. `12`). If this prints nothing, register a second account, add one expense there, and run it again.
2. Signed in as `step9@example.com`, in the Console:
   ```js
   fetch('/expenses/12/delete', {method: 'POST'}).then(r => console.log(r.status))
   ```
3. Expected: `404`.
4. `sqlite3 database.db "SELECT COUNT(*) FROM expenses WHERE id = 12;"` → still `1`.

**AC15 — deleting twice.**
1. In the Console, use the Tea id you already deleted in AC6:
   ```js
   fetch('/expenses/57/delete', {method: 'POST'}).then(r => console.log(r.status))
   ```
2. Expected: `404`.

**AC17 — HTML shown as text.** *(before AC16, since AC16 deletes this row)*
1. On `/profile`, click the trash icon on the `<b>x</b>` row.
2. Expected: the popup's Description shows the characters `<b>x</b>` exactly, not a bold **x**.
3. Click **Cancel**.

**AC16 — last expense.**
1. Delete every remaining expense of this account with the trash icons.
2. Expected: after the last one, Recent Transactions reads **You haven't logged any expenses yet.** with an **Add your first expense** link.
3. Now repeat AC3 step 3.

**Cleanup.** The `step9@example.com` account is yours to keep or remove.
It has no expenses left after AC16.

## 10. End-to-End Verification

Run the spec's tests once `/test-feature` has written them:

```bash
venv/bin/python -m pytest tests/test_09-delete-button-feature.py -v
```

Expected: all tests pass. At minimum the file must cover (using the
`auth_client` fixture from `tests/conftest.py` and `db.insert_expense`
for setup, on the throwaway test DB, never `database.db`):

1. Insert an expense → `POST /expenses/<id>/delete` with
   `data={"range": "last_3_months"}` → status 302, `Location` ends with
   `/profile?range=last_3_months` → following the redirect shows
   `Expense deleted.` → the row is gone from `expenses`.
2. The same POST again → 404.
3. `GET /expenses/<id>/delete` → 405.
4. Signed-out POST → 302 to `/login`, row still present.
5. A second user's expense → 404, row still present.
6. `/profile` HTML with an expense contains `aria-label="Delete expense"`,
   `data-action="/expenses/<id>/delete"` and `id="delete-expense-modal"`.

Then the full suite as a regression check:

```bash
venv/bin/python -m pytest
```

Expected: no new failures compared with `main` (the known UTC-vs-local
`test_showing_line_for_fresh_user_starts_at_signup_date` failure between
00:00 and 05:30 IST is a pre-existing Open Task, not caused by this step).
