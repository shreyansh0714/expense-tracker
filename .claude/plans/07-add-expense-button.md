# Plan 07 — Add expense (page + buttons)

Pairs with `.claude/specs/07-add-expense-button.md`.
Branch: `feature/add-expense-button`, branched off `main` at `7c5691e`.

> **Standing rule for whoever implements this plan:** immediately after
> finishing each task, re-open this file and tick its box. Don't batch the
> ticks to the end, and don't rely on memory for what's done. The
> checklist has to be right *while* the work is in progress, so it
> survives a context compaction or a resumed session.

## Context / Scope

Replaces the `GET /expenses/add` stub (it returns the string
`"Add expense — coming in Step 7"`) with a real form page, and adds three
links to it plus a post-save highlight on `/profile`. There is no schema
change: the `expenses` table already has every column the form needs.

**Decisions made while planning (2026-09-22):**

| Question | Decision |
|---|---|
| The ₹-prefix styles are in `profile.css`, which the add page doesn't load | Move the 3 rules to `style.css` (spec §4 updated to say so) |
| Review stops (CLAUDE.md "Session scope convention") | **Build it all, then show.** The developer chose this explicitly for this step, overriding the default stop-after-each-piece rule |
| When to commit | Spec, plan and code in **one commit at the end**, after all checks pass (SDD step 5) |

## Design Plan

### Database — `insert_expense()`

New function at the end of `database/db.py`, a copy of `create_user`'s
shape (`db.py:86-97`): `conn = get_db()` → `try:` one
`INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`
→ `conn.commit()` → `return cur.lastrowid` → `finally: conn.close()`.
It does no validation; the route validates first. `created_at` fills itself
from the column default.

### Route — `add_expense()` in `app.py`

- **Categories:** `EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]`,
  next to `DATE_RANGES`. The `<select>` loops over it and validation
  checks `category in EXPENSE_CATEGORIES`, so it's one list with exact
  case (spec FR5).
- **Login check:** the same inline 3 lines as `/profile` (`app.py:241-243`),
  with the message `Please sign in to add an expense.`. There's no
  decorator: this becomes the 4th copy, and a `login_required` decorator
  is a separate refactor, not Step 7's job.
- **Budget line:** computed once before the GET/POST split, the same way
  `profile()` builds `dashboard` before its split. It's then passed to
  both the first render and the error re-render:
  `month_start = today.replace(day=1)`,
  `month_spent = sum(row["total"] for row in get_monthly_spend(uid, month_start, today))`,
  and `budget = user["monthly_budget"]` from `get_user_by_id`.
  `get_monthly_spend` already exists (`db.py:201`), so no new query is needed.
- **Validation:** an `if/elif` chain that sets `error`, in the order of
  spec FR6, like `register` (`app.py:161-185`). The amount is parsed
  first, in a `try` like `/profile/budget` (`app.py:377-392`): strip `,`
  and spaces → `float()` → `round(x, 2)` → check `math.isfinite` and
  `> 0` → check `<= 10_000_000`.
  - **Date parsing uses `datetime.strptime(raw, "%Y-%m-%d").date()`**, not
    `date.fromisoformat`. The venv runs Python 3.13, where
    `fromisoformat` also accepts `20260922` and `2026-W38-1`, and the spec
    asks for `YYYY-MM-DD` only. The row stores `.isoformat()`, so
    `2026-9-2` is saved as `2026-09-02`.
  - Validation stays inline in the route for now. Step 8 (edit) will need
    the same checks; that's when to pull them into a shared helper, not
    before.
- **On error:** `render_template("add_expense.html", error=..., ...)` with
  the raw typed strings, status 200.
- **On success:** `insert_expense(...)` →
  `session["new_expense_id"] = new_id` → `flash("Expense added.", "success")`
  → `redirect(url_for("profile"))`.

### Profile highlight

In `profile()`, add `"new_expense_id": session.pop("new_expense_id", None)`
to the existing `dashboard` dict (`app.py:265-288`). Every
`render_template("profile.html", …)` call already passes `**dashboard`,
so this covers all 3 call sites with one line. A profile POST re-render
also clears the value, which does no harm. In the template:
`<tr{% if expense.id == new_expense_id %} class="row-new"{% endif %}>`.

CSS in `profile.css`: `.row-new td { animation: row-new-fade 2s ease-out; }`
fading from `var(--accent-light)` (existing token, `#e8f0eb`) to
`transparent`. The animation goes on the `td`s rather than the `tr`
because some browsers don't paint a row's own background under its
cells. A `@media (prefers-reduced-motion: reduce)` block sets
`animation: none`, the same as `style.css:1051` does for the modal.

### Links

| Spot | Markup | Why this way |
|---|---|---|
| Navbar (`base.html`) | `<a href="{{ url_for('add_expense') }}"{% if request.endpoint == 'add_expense' %} class="nav-active"{% endif %}>Add expense</a>` after Analytics | Copies the Profile/Analytics lines exactly |
| Recent Transactions header | Wrap the existing "View all" and a new `{{ icons.plus() }} Add expense` link, both `.card-header-link`, in `<div class="card-header-links">` | `.card-header` is `justify-content: space-between`, so a third child would land in the middle. The wrapper keeps both links on the right. "Add expense" goes first (spec FR12) |
| Never-logged empty state (×2) | `<p class="profile-empty-state">You haven't logged any expenses yet. <a href="…" class="empty-state-link">Add your first expense</a></p>` | The sentence stays word-for-word before the link, because `test_06b:346` counts that exact text |

### CSS

- **Move** (CLAUDE.md "Moving content between files"): add the 3 ₹-prefix
  rules (`profile.css:237-253`) to `style.css` → grep `style.css` for
  `.budget-input-prefix` → only then delete them from `profile.css`. The
  profile page loads `style.css` too, so it looks the same.
- **New `static/css/add_expense.css`,** loaded from
  `add_expense.html`'s `{% block head %}` like `analytics.html:5-6`. It
  holds only the budget-context line and a submit + Cancel row. Tokens
  only.

### What must not break

| Existing test | Needs | Kept by |
|---|---|---|
| `test_06b:334-335` | `View all` + `href="/analytics"` | "View all" is untouched, only wrapped |
| `test_06b:346` | `You haven't logged any expenses yet.` ≥ 2 times | Sentence unchanged, link after it |
| `test_06b:361-362`, `:115-117` | `No expenses between … Try a wider range.` with no tags in between | That message isn't touched |
| `test_06b:439` | exactly 2 `type="date"` on `/profile` | No date input added to `/profile` |

## Tasks

### Build

- [x] `database/db.py`: add `insert_expense(user_id, amount, category, date, description)`
- [x] `app.py`: add `EXPENSE_CATEGORIES`; import `insert_expense` (alphabetical, between `init_db` and `seed_db`)
- [x] `app.py`: replace the `add_expense` stub: `methods=["GET", "POST"]`, login check, budget line, FR6 validation, error re-render, success save + session + flash + redirect
- [x] `templates/add_expense.html`: new page (title, subtitle, budget line, error box, 4 fields, submit, Cancel)
- [x] CSS move: add the 3 ₹-prefix rules to `style.css` → grep that they're there → delete them from `profile.css`
- [x] `static/css/add_expense.css`: budget-context line + form actions row
- [x] `templates/base.html`: navbar "Add expense" link with `nav-active`
- [x] `app.py` `profile()`: add `new_expense_id` (popped) to the `dashboard` dict
- [x] `templates/profile.html`: `row-new` on the matching row, the card-header links wrapper + Add expense link, the 2 empty-state links
- [x] `static/css/profile.css`: `.card-header-links`, `.empty-state-link`, `.row-new` animation + reduced-motion rule
- [x] Run the existing suite (`venv/bin/python -m pytest`) as a regression check on Steps 6/6b only, not as verification of Step 7 — 69 pass, 1 fails. The failure also happens with Step 7 stashed: a UTC-vs-local-date bug that only shows between 00:00 and 05:30 IST. Logged in PROGRESS.md Open Tasks, not fixed here
- [x] Show the developer the finished build (the one review stop)

### Checks (SDD steps 2-4)

- [ ] Validate: the developer runs spec 07's Manual Verification Guide
- [ ] `/test-feature 07-add-expense-button`: all pass
- [ ] `/code-review-feature 07-add-expense-button`: not CHANGES REQUESTED

### Git finish (SDD step 5)

- [x] `.claude/PROGRESS.md`: flip `GET /expenses/add` to Implemented (it becomes `GET/POST`), add a Step 7 section
- [ ] Spendly Field Notes artifact: redraw Section 0 (project map), since a route row changed
- [ ] One commit (spec + plan + code) → push → PR → merge → back to `main`

## Verification

Use spec 07's own sections rather than repeating them here:
- §8 Acceptance Criteria (AC1-AC14) are the done list.
- §9 Manual Verification Guide is the developer's Validate pass.
- §10 End-to-End Verification is `venv/bin/python -m pytest tests/test_07-add-expense-button.py -v` plus the by-hand walk-through.

## Explicitly out of scope

Mirrors spec 07 §6:
- Edit (Step 8) and delete (Step 9)
- A full expense list
- Custom categories
- Budget alerts
- CSRF
- A modal form
- A profile-header button
- Visual polish beyond the existing form styles
- Fixing `/seed-expense`'s future dates
- Also not here: a `login_required` decorator, and a shared validation helper (wait for Step 8)
