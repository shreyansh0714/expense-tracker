# Plan 08 — Edit expense (pencil button + edit page)

**Spec:** `.claude/specs/08-edit-button-feature.md`
**Branch:** `feature/edit-button-feature`
**Checkpoints:** **one stop, at the end** (developer's choice, 2026-09-23). Build every task,
then hand over the spec's Manual Verification Guide.

> **Standing rule for whoever implements this plan:** immediately after finishing each
> task, re-open this file and tick its box. Don't batch the ticks at the end, and don't
> rely on memory to know what's done.

---

## Design Plan

### 1. Database (`database/db.py`)
- **Migration:** add `updated_at TEXT` to the `CREATE TABLE expenses` statement (for new DBs).
  For existing DBs, reuse the existing idempotent pattern at `db.py:40-47` (`try: ALTER TABLE …
  ADD COLUMN … except sqlite3.OperationalError: pass`), adding one more `ALTER TABLE expenses ADD
  COLUMN updated_at TEXT` next to the `users` loop. There's no new migration mechanism; this is
  the pattern the file already uses.
- **`get_expense(user_id, expense_id)`:** same shape as `get_user_by_id` (`db.py:110-117`), a
  `SELECT *` with `WHERE id = ? AND user_id = ?`, returning `fetchone()`.
- **`update_expense(user_id, expense_id, amount, category, date, description)`:** same shape as
  `delete_expense` (`db.py:228-238`): an `UPDATE … updated_at = datetime('now') WHERE id = ? AND
  user_id = ?`, then commit, and return `rowcount == 1`. The ownership check lives in the SQL,
  as in Step 9.
- `get_recent_expenses` already runs `SELECT *`, so `/profile` gets `updated_at` for free, with
  no change needed.

### 2. Shared validation (`app.py`)
The spec requires one validation implementation shared by Add and Edit (§5). The plan lifts
`add_expense`'s parsing and validation (`app.py:424-454`) **unchanged** into two helpers placed
above the routes, next to `build_budget_rows`:
- `parse_expense_form(form, today)` returns `(values, error)`. `values` holds `amount`,
  `category`, `expense_date`, `description`, plus the raw strings (`amount_raw`, `date_raw`)
  needed for re-rendering. The 7 checks keep the same order and the same messages.
- `expense_page_context(user, today)` returns the `page` dict now built at `app.py:412-419`
  (categories, today, budget, month_spent).

`add_expense` is rewritten to call both helpers, and its behaviour stays byte-for-byte the same
(AC15). No decorator for the login guard: the project uses the inline `if "user_id" not in
session` pattern on every route.

### 3. Edit route (`app.py`, replaces the stub at `app.py:474-476`)
`methods=["GET", "POST"]`, and in order:
1. Login guard → flash `Please sign in to edit an expense.` → `login`.
2. `expense = get_expense(session["user_id"], id)`, and `None` → `abort(404)`.
3. `filter_args` = the non-empty `range`/`start`/`end` from `request.args` (GET) or
   `request.form` (POST), using the same dict comprehension as `delete_expense`/`save_budget`.
4. **GET:** render `add_expense.html` with `expense=expense`, `filter_args=filter_args`,
   `amount=expense["amount"]`, `category`, `date`, `description or ""`, and `**page`.
5. **POST:** `parse_expense_form`. On an error, re-render (status 200) with the typed values +
   `expense` + `filter_args`.
6. **No-change check:** `amount == expense["amount"]` and `category ==` and
   `expense_date.isoformat() == expense["date"]` and `(description or None) ==
   expense["description"]`. If all match, flash `No changes to save.` (success) and redirect to
   `profile` with `**filter_args`.
7. Otherwise `update_expense(...)`, and `False` → `abort(404)`. Then
   `session["new_expense_id"] = id`, flash `Expense updated.`, and redirect to `profile` with
   `**filter_args`.

Import `get_expense` and `update_expense` in the `database.db` import block. They don't clash
with any route name, so no alias is needed.

### 4. One template for both pages (`templates/add_expense.html`)
The template switches on `expense` (it's only passed by the edit route), so **`add_expense`
passes nothing new** and the Add page keeps rendering exactly as before:
- `<title>`, `h1`, subtitle, form `action`, submit label → an `{% if expense %}` switch between
  Edit and Add text (Edit uses `url_for('edit_expense', id=expense.id)` and **Save changes**).
- After the budget line, edit only:
  `<p class="expense-original">Currently: {{ expense.date }} · {{ expense.category }} ·
  ₹{{ expense.amount|inr }} · {{ expense.description or "—" }}</p>` and
  `<p class="expense-edited">{% if expense.updated_at %}Last edited {{ expense.updated_at[:10] }}{%
  else %}Never edited{% endif %}</p>`. Both are autoescaped (AC16).
- Inside the form, edit only: `{% for key, value in filter_args.items() %}<input type="hidden"
  …>{% endfor %}`.
- Cancel: `url_for('profile', **filter_args)` when editing, otherwise `url_for('profile')`.

### 5. Profile table (`templates/profile.html:185-195`)
- Pencil, placed before the trash button: `<a class="row-edit-btn" aria-label="Edit expense"
  href="{{ url_for('edit_expense', id=expense.id, range=active_range, start=range_start.isoformat()
  if active_range == 'custom' else none, end=… ) }}">{{ icons.edit() }}</a>`. `url_for` drops
  `None` args, so non-custom ranges produce only `?range=…`.
- Description cell: `{{ expense.description or "—" }}{% if expense.updated_at %} <span
  class="edited-tag">edited</span>{% endif %}`.

### 6. CSS (tokens only)
- `profile.css`: the Actions `th:last-child` width goes from `2.5rem` to about `4.75rem` (two
  icons). Change the `.row-delete-btn` rule to `.row-delete-btn, .row-edit-btn` so they share one
  look, and add `.row-edit-btn:hover { color: var(--accent); background: var(--accent-light); }`
  and `.edited-tag` (`font-size: 0.75rem; color: var(--ink-muted); font-style: italic;`).
- `add_expense.css`: `.expense-original` and `.expense-edited` (`0.85rem`, `--ink-muted`), under
  the existing section banner.

### 7. Added after Build (developer request, 2026-09-23): spec FR19 + FR20
- **Scroll (FR19):** a plain URL anchor. `url_for('profile', _anchor=f"expense-{id}", **filter_args)`
  on both edit redirects, `id="expense-{{ expense.id }}"` on each row, and
  `scroll-margin-top` on the rows so the sticky navbar (`style.css:94`) doesn't cover them.
  `style.css:76` already sets `scroll-behavior: smooth`, so no JS is needed.
- **Back arrow (FR20):** a browser can't delete a history entry, so the edit page detects that it
  was reached via Back/Forward (`pageshow` with `event.persisted` for bfcache, or navigation type
  `back_forward`) and calls `location.replace()` to go to the same profile+anchor URL. The URL
  is built once in the template (`back_to`) and used by both the form's `data-back-to` and the
  Cancel link.

### Judgment calls
| Call | Why |
|---|---|
| Switch on `expense` in the template instead of passing labels from both routes | Leaves `add_expense`'s render call untouched, which keeps AC15 easy to trust |
| Helpers instead of copying the 30 lines of validation | The spec requires it (§5); copied rules drift |
| No Plan subagent for design | The spec already pins every route/DB/template decision; this plan only sequences them |

---

## Tasks

- [x] 0. Save this plan as `.claude/plans/08-edit-button-feature.md`
- [x] 1. `database/db.py`: `updated_at` in `CREATE TABLE expenses` + idempotent `ALTER TABLE` in `init_db()`
- [x] 2. `database/db.py`: add `get_expense()` and `update_expense()`
- [x] 3. `app.py`: add `parse_expense_form()` + `expense_page_context()`, rewrite `add_expense` to use them (same behaviour)
- [x] 4. `app.py`: import the two new DB helpers, replace the `edit_expense` stub with the GET/POST route
- [x] 5. `templates/add_expense.html`: `expense` switch (title/heading/subtitle/action/button/Cancel), Currently + edited lines, filter hidden inputs
- [x] 6. `static/css/add_expense.css`: `.expense-original`, `.expense-edited`
- [x] 7. `templates/profile.html`: pencil link before the trash button, `edited` tag in the Description cell
- [x] 8. `static/css/profile.css`: wider Actions column, shared `.row-edit-btn` style + hover, `.edited-tag`
- [x] 9. Smoke-check that the app starts (`venv/bin/python -c "import app"`) with no errors against a throwaway DB copy, not the real `database.db`
- [x] 9a. FR19 scroll: `#expense-<id>` anchor on both edit redirects (`app.py`), row `id` (`profile.html`), `scroll-margin-top` (`profile.css`)
- [x] 9b. FR20 Back arrow: `back_to` URL + `id`/`data-back-to` on the edit form and Cancel (`add_expense.html`), new IIFE in `static/js/main.js`
- [x] 10. **Stop.** Hand over the spec's Manual Verification Guide (§9) to the developer
- [ ] 11. `/test-feature 08-edit-button-feature` — **skipped by the developer, 2026-09-23**
- [ ] 12. `/code-review-feature 08-edit-button-feature` — **skipped by the developer, 2026-09-23**
- [ ] 13. Git finish: flip the PROGRESS.md route row + add a Step 8 section, commit (no Claude attribution), push, PR, merge

---

## Explicitly out of scope
Same as spec §6: editing from anywhere but the Recent Transactions rows, an edit modal or inline
editing or any new JS, edit history/undo, local-time conversion of `updated_at`, bulk edit, CSRF,
changes to Add or Delete behaviour, and visual polish beyond tokens.

## Verification
- Manual: spec §9 Manual Verification Guide (AC1–AC16), run by the developer at task 10.
- Automated: spec §10 End-to-End Verification via `/test-feature` (task 11), then the full
  `venv/bin/python -m pytest` regression run.
- Review: `/code-review-feature` (task 12). Commit only when all three pass.
