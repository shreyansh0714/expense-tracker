# Spec 07 — Add expense (page + buttons)

**Status:** Draft — not yet implemented
**Branch:** `feature/add-expense-button` (branched off `main` at `7c5691e`,
after the Step 6b merge, PR #10)
**Date:** 2026-09-22

**Supersedes one line of `06b-profile-dashboard-restructure.md`:**

| Superseded | What 06b said | What 07 says |
|---|---|---|
| Empty states (`06b:204`) | "Neither message is a link. `/expenses/add` is a Step 7 stub … so nothing on this page may point at it." | The **never-logged** message ("You haven't logged any expenses yet.") becomes a link to `/expenses/add`. The **filter-matched-nothing** message ("No expenses between … Try a wider range.") stays plain text, unchanged |

**Design reference:** none exists yet. The developer will make a mockup
*from* this spec. This spec fixes content and behaviour only. Any later
visual polish must not add, remove or reword the content listed here
(see CLAUDE.md, "Mockup content convention").

---

## 1. Problem Statement

Spendly can show expenses (profile dashboard, Steps 4-6b) but a user has
no way to create one. The only expenses in the app today come from
`seed_db()` or the `/seed-expense` slash command. `GET /expenses/add` is a
stub in `app.py` that returns the plain string
`"Add expense — coming in Step 7"`, and nothing links to it.

This step makes adding an expense a real feature:

1. A form page at `/expenses/add` that saves one expense for the signed-in
   user.
2. A read-only budget line on that page, so the user sees how much of this
   month's budget is already used before adding more.
3. Three ways to reach the page: a navbar link, a link on the Recent
   Transactions card, and the dashboard's "never logged anything" message.
4. After saving, the user lands on `/profile`, sees an "Expense added."
   toast and the new row briefly highlighted.

## 2. Functional Requirements

### The page — `GET /expenses/add`

- **FR1 — Login required.** A signed-out visitor (no `user_id` in the
  session) is redirected to `url_for('login')` with the flash message
  `Please sign in to add an expense.` (category `error`). Applies to GET
  and POST.
- **FR2 — Template.** Renders a new `templates/add_expense.html` that
  extends `base.html`. Layout reuses the existing form layout from
  `register.html` / `login.html`: `section.auth-section > div.auth-container`,
  a `div.auth-header` with `h1.auth-title` "Add an expense" and
  `p.auth-subtitle` "Log something you spent money on.", then a
  `div.auth-card` holding the form.
- **FR3 — Budget line (read-only).** Above the form, inside the card, one
  line about the **current calendar month** (1st of this month through
  today):
  - Budget set (`users.monthly_budget` is not NULL, including `0`):
    `₹<spent> of ₹<budget> used this month`, both amounts through the
    existing `inr` filter, e.g. `₹4,500.00 of ₹10,000.00 used this month`.
  - No budget set (`monthly_budget` is NULL): `No monthly budget set` —
    plain text, not a link.
  - `<spent>` is the sum of the user's expenses dated from the 1st of this
    month through today (`₹0.00` if none). The element has class
    `budget-context`.
- **FR4 — Form fields.** One `<form method="post">` posting to
  `url_for('add_expense')`, fields in this order:

  | Field `name` | Control | Required | Default on first load |
  |---|---|---|---|
  | `amount` | `<input type="text" inputmode="decimal">` with the `₹` prefix, reusing `.budget-input-group` / `.budget-input-prefix` | Yes | empty |
  | `category` | `<select>`: first option `value=""` "Choose a category", then the 7 categories in this order: Food, Transport, Bills, Health, Entertainment, Shopping, Other (value = label, exact case) | Yes | "Choose a category" |
  | `date` | `<input type="date">` with `max` = today (`YYYY-MM-DD`) | Yes | today |
  | `description` | `<input type="text" maxlength="200">`, label "Description (optional)" | No | empty |

  Each field is a `div.form-group > label[for] + control.form-input`.
  Below the fields: a `button.btn-submit` labelled `Add expense`, and a
  `Cancel` link to `url_for('profile')`.
- **FR5 — Single source for categories.** The 7 categories live in one
  constant, `EXPENSE_CATEGORIES`, in `app.py`. It is used both to render
  the `<select>` options and to validate the submitted value.

### Saving — `POST /expenses/add`

- **FR6 — Validation, in this order; stop at the first failure.**

  | # | Check | Error message (exact) |
  |---|---|---|
  | 1 | `amount` missing or blank after trimming | `Please enter an amount.` |
  | 2 | After removing commas and spaces: not a number, not finite (`nan`, `inf`), or ≤ 0 after rounding to 2 decimals | `Amount must be a number greater than 0.` |
  | 3 | Rounded amount > 10000000 (₹1 crore) | `Amount can't be more than ₹1,00,00,000.00.` |
  | 4 | `category` not exactly one of `EXPENSE_CATEGORIES` (blank, unknown, or wrong case like `food`) | `Please choose a category.` |
  | 5 | `date` missing or not a valid `YYYY-MM-DD` date | `Please enter a valid date.` |
  | 6 | `date` later than today | `Date can't be in the future.` |
  | 7 | `description` longer than 200 characters after trimming | `Description must be 200 characters or fewer.` |

- **FR7 — On a validation error.** Re-render `add_expense.html` with
  **status 200** (same as `register`), showing the one message in
  `<div class="auth-error">` inside the card, with every field keeping
  what the user typed (raw `amount` text, chosen `category`, `date`,
  `description`) and the budget line still shown. **No row is written.**
- **FR8 — On success.**
  1. Insert one row into `expenses` via a new `insert_expense()` helper in
     `database/db.py`: `user_id` = `session["user_id"]` (never from the
     form), `amount` = rounded to 2 decimals, `category` = as submitted,
     `date` = `YYYY-MM-DD`, `description` = trimmed text, or `NULL` if
     blank.
  2. Store the new row's id in `session["new_expense_id"]`.
  3. `flash("Expense added.", "success")`.
  4. Redirect (302) to `url_for('profile')` with no query string (so the
     default "This month" range is shown).

### After saving — `/profile`

- **FR9 — Toast.** "Expense added." shows through the existing toast in
  `base.html` (`.toast.toast-success`): it already slides in and
  auto-hides after 4 seconds (`static/js/main.js`, "Auto-dismiss flashed
  toasts"). No new toast code.
- **FR10 — Row highlight.** `profile()` removes `new_expense_id` from the
  session (`session.pop`) on every load and passes it to the template. In
  Recent Transactions, the `<tr>` whose `expense.id` equals it gets class
  `row-new`. `.row-new` plays a ~2 second animation from a soft tint of
  the `--accent` token back to the normal row background. Under
  `@media (prefers-reduced-motion: reduce)` there is no animation. Because
  the value is popped, reloading `/profile` doesn't highlight the row a
  second time.

### Buttons / links to the page

- **FR11 — Navbar.** In `base.html`, only when signed in, add an
  `Add expense` link to `url_for('add_expense')` after Analytics. It gets
  `class="nav-active"` when `request.endpoint == 'add_expense'`, same
  pattern as Profile/Analytics. Signed-out visitors don't see it.
- **FR12 — Recent Transactions card.** In `profile.html`'s Recent
  Transactions `div.card-header`, add a link `{{ icons.plus() }} Add expense`
  to `url_for('add_expense')`, placed before "View all". It is always
  shown, including when the card is empty.
- **FR13 — Never-logged empty state.** In **both** places
  `You haven't logged any expenses yet.` appears in `profile.html` (Recent
  Transactions and By Category), follow the sentence with a link
  `Add your first expense` to `url_for('add_expense')`. The
  filter-matched-nothing message is not changed.

## 3. APIs

| Method + path | Input | Output |
|---|---|---|
| `GET /expenses/add` | Session `user_id` | Signed in: 200, `add_expense.html`. Signed out: 302 → `/login` + error flash |
| `POST /expenses/add` | Session `user_id`; form fields `amount`, `category`, `date`, `description` (all strings) | Valid: 302 → `/profile`, one new `expenses` row, success flash, `session["new_expense_id"]`. Invalid: 200, form re-rendered with one error. Signed out: 302 → `/login`, nothing written |
| `GET /profile` (changed) | Additionally pops `session["new_expense_id"]` | Adds `class="row-new"` to the matching Recent Transactions row, if shown |

Row written (existing `expenses` table, no schema change):

| Column | Value |
|---|---|
| `user_id` | `session["user_id"]` |
| `amount` | `REAL`, rounded to 2 decimals, e.g. `"1,250.505"` → `1250.51` |
| `category` | One of the 7, exact case |
| `date` | `TEXT` `YYYY-MM-DD`, ≤ today |
| `description` | Trimmed text ≤ 200 chars, or `NULL` |
| `created_at` | Filled by the column default |

Template context for `add_expense.html`: `categories` (the list), `today`
(`YYYY-MM-DD`), `budget` (float or `None`), `month_spent` (float),
`error` (string or `None`), and the typed values `amount`, `category`,
`date`, `description`.

## 4. Files and Interfaces Involved

| File | Change |
|---|---|
| `database/db.py` | New `insert_expense(user_id, amount, category, date, description)` → returns the new row id. Same shape as `create_user` (try / `commit` / `return cur.lastrowid` / finally `close`), `?` placeholders only |
| `app.py` | New `EXPENSE_CATEGORIES` constant. `add_expense()` stub (`@app.route("/expenses/add")`) replaced: `methods=["GET", "POST"]`, inline login check like `/profile`, FR6 validation, FR3 budget line (reuse `get_user_by_id` for `monthly_budget` and `get_monthly_spend` for this month's spend), FR8 save. `profile()`: pop `new_expense_id`, pass it to the template. Import `insert_expense` |
| `templates/add_expense.html` | New. The page from FR2-FR4 and FR7 |
| `templates/base.html` | Navbar link (FR11) |
| `templates/profile.html` | Card-header link (FR12), empty-state links (FR13), `row-new` class (FR10) |
| `static/css/add_expense.css` | New, loaded via `{% block head %}` in `add_expense.html`. Page-only styles (budget line, Cancel link spacing). Tokens only |
| `static/css/profile.css` | `.row-new` animation + reduced-motion rule, styles for the card-header add link and empty-state link. The 3 ₹-prefix rules (`.budget-input-group`, `.budget-input-prefix`, `.budget-input-group .form-input`) move **out** of here |
| `static/css/style.css` | Receives those 3 ₹-prefix rules unchanged, because two pages (profile + add expense) now use them |

The stubs `edit_expense` and `delete_expense` are **not** touched.

## 5. Constraints

- Flask + sqlite3 only; no new pip packages, no ORM, no JS framework.
- All SQL lives in `database/db.py` and uses `?` placeholders.
- Every internal link uses `url_for(...)`, never a hardcoded path.
- Colours, fonts and spacing only through `:root` tokens in `style.css`;
  no new hardcoded hex or px value where a token exists.
- Numbers are parsed like the budget box in `POST /profile/budget`: strip
  commas and spaces, `float()`, `math.isfinite()` check.
- Money is shown only through the `inr` filter (Indian grouping, 2
  decimals).
- `user_id` comes only from the session; any `user_id` form field is
  ignored.
- Icons come from `templates/_icons.html` (`icons.plus()` already exists)
  and always sit next to visible text.
- The app keeps running on port 5001 with `debug=True`.

## 6. Out of Scope

- Editing an expense (Step 8) or deleting one (Step 9): no edit/delete
  links anywhere.
- A full list of all expenses (the Analytics page is a separate, later
  feature).
- Custom / free-text categories, or adding new categories.
- Budget alerts or warnings when this expense would go over budget (the
  budget line is informational only; see PROGRESS.md Future Features).
- CSRF protection (tracked in PROGRESS.md Open Tasks as its own spec).
- A modal version of the form, or an "Add expense" button in the profile
  header next to "Edit profile".
- Visual polish beyond reusing existing form styles. A later
  `spendly-ui-polish` pass from the developer's mockup may restyle the
  page without changing its content.
- Fixing `/seed-expense`'s future-dated rows (separate Open Task).

## 7. Edge Cases and Error Handling

| Case | Behaviour |
|---|---|
| Signed out, GET or POST | 302 → `/login`, flash `Please sign in to add an expense.`, nothing written |
| `amount` = `"1,250.50"` or `" 1 250.50 "` | Accepted as `1250.5` |
| `amount` = `"abc"`, `"-5"`, `"0"`, `"nan"`, `"inf"` | `Amount must be a number greater than 0.` |
| `amount` = `"0.004"` (rounds to `0.00`) | `Amount must be a number greater than 0.` |
| `amount` = `"10000000"` | Accepted (exactly the max) |
| `amount` = `"10000000.01"` | `Amount can't be more than ₹1,00,00,000.00.` |
| `category` = `"food"`, `"Groceries"`, blank, or missing | `Please choose a category.` |
| `date` = `"22-09-2026"`, `"2026-02-30"`, blank | `Please enter a valid date.` |
| `date` = tomorrow | `Date can't be in the future.` (the `max` attribute also blocks this in the browser; the server check is the real guard) |
| `description` = spaces only | Saved as `NULL`; shows as `—` in Recent Transactions |
| `description` of 201+ characters sent by hand (bypassing `maxlength`) | `Description must be 200 characters or fewer.` |
| Several fields wrong at once | Only the first failing check in FR6's order is shown |
| Saved expense is dated before this month | Toast shows; the row isn't in the default "This month" Recent Transactions, so nothing is highlighted. Expected, not a bug |
| Saved expense isn't among the 5 most recent this month (older date) | Same as above: toast shows, no highlight |
| `monthly_budget` = `0` | `₹<spent> of ₹0.00 used this month` |
| DB write fails (`sqlite3` error) | Not caught; Flask's normal 500. No partial row is possible (single INSERT) |
| Session `user_id` points to a deleted user | Foreign key fails on insert → 500. Same as other routes today; not handled here |

## 8. Acceptance Criteria

- [ ] **AC1** Signed out, `GET /expenses/add` → 302 to `/login`; the next page shows the toast `Please sign in to add an expense.`
- [ ] **AC2** Signed out, `POST /expenses/add` with valid fields → 302 to `/login`; `expenses` table row count unchanged.
- [ ] **AC3** Signed in, `GET /expenses/add` → 200; the HTML contains `Add an expense`, inputs named `amount`, `category`, `date`, `description`, a `<select name="category">` whose options are `""` then `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other` in that order, a date input whose `value` and `max` are today's `YYYY-MM-DD`, `maxlength="200"` on description, a submit button `Add expense`, and a link to `/profile` labelled `Cancel`.
- [ ] **AC4** Budget line: a user with `monthly_budget` 10000 and expenses of 4000 + 500 dated this month (and one of 999 dated last month) sees `₹4,500.00 of ₹10,000.00 used this month`. A user with `monthly_budget` NULL sees `No monthly budget set`.
- [ ] **AC5** Signed in, POST `amount=1,250.505`, `category=Food`, `date=<today>`, `description="  Lunch  "` → 302 to `/profile`; exactly one new row for that user with `amount` 1250.51, `category` `Food`, `date` today, `description` `Lunch`.
- [ ] **AC6** Following that redirect, `/profile` contains `Expense added.` inside an element with class `toast-success`.
- [ ] **AC7** That `/profile` response has `class="row-new"` on the new expense's row; a second `GET /profile` has no `row-new` anywhere.
- [ ] **AC8** Each of the 7 invalid inputs in §7 (one per FR6 row) → status 200, the exact FR6 message present, no new row, and the typed values present back in the form.
- [ ] **AC9** POST with a blank `description` stores `NULL`.
- [ ] **AC10** POST with an extra field `user_id=<another user's id>` saves the row under the signed-in user.
- [ ] **AC11** Signed in, every page's navbar has an `Add expense` link to `/expenses/add`; on `/expenses/add` it has `class="nav-active"`. Signed out, the navbar has no link to `/expenses/add`.
- [ ] **AC12** `/profile`'s Recent Transactions card header contains a link to `/expenses/add` with text `Add expense`, whether or not the user has expenses.
- [ ] **AC13** A user with no expenses sees `You haven't logged any expenses yet.` followed by a link `Add your first expense` to `/expenses/add`, in both the Recent Transactions and By Category cards. A user who has expenses but none in the chosen range sees `No expenses between … Try a wider range.` with no link to `/expenses/add` next to it.
- [ ] **AC14** (visual, manual only) The highlighted row fades from a soft green tint back to normal in about 2 seconds; with "reduce motion" turned on in the OS, there is no fade animation.

## 9. Manual Verification Guide

**Setup (do once).** In a terminal, from the `expense-tracker` folder:

```bash
source venv/bin/activate
python app.py
```

Leave it running. Open **http://localhost:5001** in Chrome. To register a
fresh account for testing, go to **http://localhost:5001/register** and
sign up with e.g. `Step Seven` / `step7@example.com` / `testpass1`.
Keep a **second terminal** open in the same folder for the `sqlite3`
checks below (they only read, they don't change anything).

---

**AC1 — signed-out GET is redirected.**
1. Click **Sign out** in the navbar (or visit http://localhost:5001/logout).
2. Type **http://localhost:5001/expenses/add** into the address bar, press Enter.
3. Expected: the address bar now shows `/login`, and a toast in the corner reads **Please sign in to add an expense.**

**AC2 — signed-out POST writes nothing.**
1. Still signed out, in the second terminal run:
   ```bash
   sqlite3 database.db "SELECT COUNT(*) FROM expenses;"
   ```
   Note the number.
2. Run:
   ```bash
   curl -i -X POST http://localhost:5001/expenses/add -d "amount=100&category=Food&date=$(date +%F)&description=test"
   ```
3. Expected: the first line is `HTTP/1.1 302 FOUND` and there's a line `Location: /login`.
4. Re-run the `COUNT(*)` command: same number as step 1.

**AC3 — the page and its form.**
1. Sign in as your test account. Visit **http://localhost:5001/expenses/add**.
2. Expected on screen: heading **Add an expense**, subtitle **Log something you spent money on.**, fields **Amount** (with a ₹ in front), **Category**, **Date**, **Description (optional)**, a button **Add expense**, and a **Cancel** link.
3. Click the Category dropdown: **Choose a category**, then Food, Transport, Bills, Health, Entertainment, Shopping, Other, in that order.
4. The Date box already shows today. Click it: in the calendar, days after today are greyed out.
5. Click into Description and hold a key down: typing stops at 200 characters.
6. Click **Cancel**: you land on `/profile`.

**AC4 — budget line.**
1. On `/profile`, if you have no monthly budget, the budget control says **Add monthly budget**. Go to **http://localhost:5001/expenses/add**: under the heading it reads **No monthly budget set**.
2. Back on `/profile`, set a monthly budget of `10000` using the budget control.
3. Add two expenses via the form, both dated today: `4000` (Food) and `500` (Transport).
4. Open **http://localhost:5001/expenses/add** again. Expected: **₹4,500.00 of ₹10,000.00 used this month** (plus any other expenses you already had this month).
5. Optional: add a `999` expense dated any day last month, reopen the page: the line does **not** change.

**AC5 — a valid save.**
1. On the add page enter Amount `1,250.505`, Category `Food`, Date today, Description `  Lunch  ` (with spaces around it). Click **Add expense**.
2. Expected: you land on `/profile`.
3. In the second terminal:
   ```bash
   sqlite3 database.db "SELECT id, user_id, amount, category, date, description FROM expenses ORDER BY id DESC LIMIT 1;"
   ```
   Expected output like `57|9|1250.51|Food|2026-09-22|Lunch`: amount `1250.51`, category `Food`, today's date, description `Lunch` with no spaces around it. `user_id` is your test account's id; check it with `sqlite3 database.db "SELECT id FROM users WHERE email='step7@example.com';"`.

**AC6 — toast.**
1. Right after step 1 of AC5, look at the corner of the screen: a toast reads **Expense added.** with a green left edge, slides in and disappears after about 4 seconds.

**AC7 — highlight shows once.**
1. Right after saving, in Recent Transactions the new `Lunch` row briefly has a green background that fades out.
2. To check the class: right-click the row → **Inspect**. The Elements panel highlights a `<tr class="row-new">`.
3. Press **Cmd+R** to reload. The row doesn't flash again; in Inspect, the `<tr>` no longer has `row-new`.

**AC8 — each error message.** On the add page, try each line below one at a time (fill every other field validly: Amount `100`, Category `Food`, Date today). After each click of **Add expense**, check that the red message matches exactly, the page stays on `/expenses/add`, and what you typed is still in the boxes.

| Enter | Expected message |
|---|---|
| Amount empty | `Please enter an amount.` |
| Amount `abc` (also try `-5`, `0`, `0.004`) | `Amount must be a number greater than 0.` |
| Amount `10000000.01` | `Amount can't be more than ₹1,00,00,000.00.` |
| Category left on "Choose a category" | `Please choose a category.` |

The date and description checks can't be triggered from the browser (the date picker blocks future days, `maxlength` blocks long text), so use `curl` with your signed-in cookie:
1. In Chrome on the add page: **DevTools** (Cmd+Option+I) → **Application** tab → left sidebar **Storage → Cookies** → click `http://localhost:5001` → copy the **Value** of the `session` row.
2. Run each command, replacing `PASTE` with that value:
   ```bash
   curl -s -X POST http://localhost:5001/expenses/add -b "session=PASTE" -d "amount=100&category=Food&date=2026-02-30" | grep -o "Please enter a valid date."
   curl -s -X POST http://localhost:5001/expenses/add -b "session=PASTE" -d "amount=100&category=Food&date=2099-01-01" | grep -o "Date can't be in the future."
   curl -s -X POST http://localhost:5001/expenses/add -b "session=PASTE" -d "amount=100&category=Food&date=$(date +%F)&description=$(printf 'a%.0s' {1..201})" | grep -o "Description must be 200 characters or fewer."
   curl -s -X POST http://localhost:5001/expenses/add -b "session=PASTE" -d "amount=100&category=food&date=$(date +%F)" | grep -o "Please choose a category."
   ```
   Expected: each prints its message once. If a command prints nothing, that check failed.
3. Re-run the `ORDER BY id DESC LIMIT 1` query from AC5: the newest row is still the one from AC5, so none of these saved anything.

**AC9 — blank description is NULL.**
1. Add an expense with the Description box empty.
2. Run:
   ```bash
   sqlite3 database.db "SELECT description IS NULL FROM expenses ORDER BY id DESC LIMIT 1;"
   ```
   Expected: `1`. On `/profile` the row's Description column shows `—`.

**AC10 — user_id can't be forced.**
1. Using the cookie from AC8:
   ```bash
   curl -s -o /dev/null -X POST http://localhost:5001/expenses/add -b "session=PASTE" -d "amount=77&category=Other&date=$(date +%F)&user_id=1"
   sqlite3 database.db "SELECT user_id, amount FROM expenses ORDER BY id DESC LIMIT 1;"
   ```
   Expected: `user_id` is **your** test account's id (not `1`), amount `77.0`.

**AC11 — navbar link.**
1. Signed in, on any page: the navbar shows **Profile · Analytics · Add expense · Sign out**.
2. Click **Add expense**: the link now looks active (same style as Profile when you're on `/profile`).
3. Sign out: the navbar no longer has **Add expense**.

**AC12 — card link.**
1. On `/profile`, the **Recent Transactions** card's title row shows **+ Add expense** next to **View all**. Click it: you land on `/expenses/add`.
2. Pick **Last month** or a date range with nothing in it: the link is still there.

**AC13 — empty-state links.**
1. Register a second brand-new account (e.g. `empty@example.com`). On its `/profile`, both **Recent Transactions** and **By Category** read **You haven't logged any expenses yet.** followed by a link **Add your first expense**. Click one: you land on `/expenses/add`.
2. Switch back to your first test account. Enter a custom range with no expenses (e.g. From `2020-01-01` To `2020-01-31`): the cards read **No expenses between … Try a wider range.** with **no** "Add your first expense" link.

**AC14 — animation + reduced motion.**
1. Add an expense dated today and watch the new row: the green tint fades out over about 2 seconds.
2. Turn on reduced motion: **System Settings → Accessibility → Display → Reduce motion** (on). Add another expense. The row shows no fading animation.
3. Turn **Reduce motion** back off.

**Cleanup (optional).** The expenses you added are real rows in
`database.db`. To remove the test account's rows (change the email if you
used a different one):

```bash
sqlite3 database.db "DELETE FROM expenses WHERE user_id = (SELECT id FROM users WHERE email='step7@example.com');"
```

## 10. End-to-End Verification

Automated (after `/test-feature 07-add-expense-button` writes the tests):

```bash
venv/bin/python -m pytest tests/test_07-add-expense-button.py -v
```

Expected: every test passes. The run uses a throwaway database via
`tests/conftest.py`, never `database.db`.

By hand, one full pass:
1. `python app.py`, register a new account at http://localhost:5001/register.
2. `/profile` shows **You haven't logged any expenses yet. Add your first expense**. Click the link.
3. Page shows **No monthly budget set**. Enter `250`, `Transport`, today, `Auto to office`, click **Add expense**.
4. You land on `/profile`: toast **Expense added.**, the `Auto to office` row fades from green, the stat tiles show ₹250.00 and 1 transaction.
5. `sqlite3 database.db "SELECT amount, category, date, description FROM expenses ORDER BY id DESC LIMIT 1;"` prints `250.0|Transport|<today>|Auto to office`.
