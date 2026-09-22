# Plan 09 — Delete expense (button + confirm popup)

Paired with spec `.claude/specs/09-delete-button-feature.md`. Branch `feature/delete-button-feature`.
On approval, this file gets saved to `.claude/plans/09-delete-button-feature.md` (Task 0).

**Standing rule for whoever implements this:** right after you finish each task, re-open this file and check its box. Don't save the checkboxes up for the end of the session.

## Context

Step 7 lets users add expenses, but they can't remove one. `/expenses/<id>/delete` is still a stub that returns `"Delete expense — coming in Step 9"`. Spec 09 turns it into a real feature: a trash icon on each Recent Transactions row, a confirm popup showing that expense, a red fade on the row, then a POST that deletes it and returns to `/profile` with the same filter and an "Expense deleted." toast.

Decisions made after the spec was written (from the /implement-plan interview):

| Question | Answer |
|---|---|
| How the row leaves | Red flash, then fade only. No collapse |
| Popup opening animation | Same `crumple-open` as the Edit profile popup |
| Checkpoints | Stop after the backend, and again after the UI |

## Design Plan

### Backend
- **`database/db.py` → `delete_expense(user_id, expense_id)`**, placed after `insert_expense` and shaped like it: `get_db()`, `DELETE FROM expenses WHERE id = ? AND user_id = ?`, commit, close in `finally`, `return cur.rowcount == 1`. The `AND user_id = ?` is the ownership check. There's no separate "load, then compare owner" step, so there's nothing to race.
- **`app.py`**: add `abort` to the flask import (line 6). Import the helper as `delete_expense as db_delete_expense`, because the route function is also called `delete_expense`, and renaming the route would change the `url_for('delete_expense')` endpoint. The stub at line 478 becomes `methods=["POST"]`:
  1. Signed out → flash `Please sign in to delete an expense.` (error) and redirect to `login`. This copies `add_expense`'s inline check. No decorator yet: that would be an abstraction added in the middle of a feature.
  2. `db_delete_expense(...)` returns False → `abort(404)`.
  3. `filter_args`: the same dict comprehension as `save_budget()`. Then flash `Expense deleted.` and redirect to `url_for("profile", **filter_args)`.

### UI
- **`templates/_icons.html` → `trash(size=16)`**: the Feather "trash-2" glyph, using the same `_svg()` helper as `edit`. The SVG stays `aria-hidden`. The button's `aria-label` is the real label.
- **`templates/profile.html` table**: an empty `<th></th>` after Amount, plus a 5th `<td>` per row holding `<button type="button" class="row-delete-btn" aria-label="Delete expense" data-action=… data-date=… data-description=… data-category=… data-amount=…>{{ icons.trash() }}</button>`. Jinja's autoescape keeps `<b>x</b>` safe inside the attributes.
- **`templates/profile.html` popup** `#delete-expense-modal`: placed after `#edit-profile-modal`, wrapped in its own `{% if recent_expenses %}` so it isn't rendered when the table is empty (spec AC3). Its markup matches the edit-profile popup's: overlay, `.modal-content`, × button, and reuse of `.edit-profile-card` for the card look. The content is an `h2` "Delete this expense?", a `<dl>` with `data-field` slots, "This can't be undone.", and a `form#delete-expense-form method="post"`. The form holds the same hidden `range`/`start`/`end` inputs as the `budget_form` macro. Two copies of those inputs aren't worth a shared macro yet. Buttons: Cancel = existing `.btn-ghost` + `data-modal-close`; Delete = `.btn-submit.btn-danger`.
- **`static/js/main.js`**: a new IIFE after the edit-profile one, guarded with `if (!modal) return;`.
  - Clicking a trash button fills the popup with `textContent`, sets `form.action`, and opens the popup with the same `.opening` reflow trick (420 ms) as the edit-profile popup.
  - Close buttons are wired per popup, the same way the other popups do it.
  - On submit: `preventDefault`, disable Delete, close the popup, then:
    - reduced motion → submit right away;
    - otherwise → add `row-deleting` to the row, and submit on `animationend` filtered to `animationName === "row-delete"` (so a still-running Step 7 `row-new-fade` can't trigger an early submit). A 1 s fallback timer also submits, and a `sent` flag guarantees only one submit.
- **CSS**:
  - `style.css`: add `#delete-expense-modal .modal-content` to the existing 480px selector (line 1050). Add `.btn-danger` (`--danger` background, `--paper-card` text, `--ink` on hover, dimmed when `:disabled`).
  - `profile.css`: a new `/* --- Delete expense (Step 9) --- */` block after the Step 7 block. It holds: a 2.5rem last column (needed because the table uses `table-layout: fixed`), `.row-delete-btn` (muted, turns `--danger` on hover), the popup's `dl` grid, the warning line, the button row, and `.row-deleting td` with `row-delete` keyframes (hold `--danger-light`/`--danger` for the first 30%, then fade to `opacity: 0` over 0.6 s total). Also add `.row-deleting td { animation: none; }` to the existing reduced-motion block.

### Spec corrections this plan requires

| Where in the spec | Now says | Change to | Why |
|---|---|---|---|
| FR7 step 3, Problem Statement item 3, AC6 | "fades to transparent and collapses" / "fades out" | Red flash, then fade. No collapse | Developer's decision |
| FR4 | (no mention of an opening animation) | The popup opens with the edit-profile popup's `crumple-open` (`.opening`) animation, which is skipped under reduced motion | Developer's decision |
| FR5 Delete button | "white text" | `--paper-card` text | No white token exists, and new hex values aren't allowed |
| AC8 + Manual guide AC8 step 3 | `Location: /profile` | `Location: /profile?range=this_month` when deleting from a plain `/profile` | The hidden `range` input is always sent (`active_range` defaults to `this_month`), the same as the budget form |

## Tasks

- [x] 0. Save this plan as `.claude/plans/09-delete-button-feature.md`, and apply the four spec corrections from the table above to `.claude/specs/09-delete-button-feature.md`

**Checkpoint 1 — backend**
- [x] 1. `database/db.py`: add `delete_expense(user_id, expense_id)`
- [x] 2. `app.py`: add `abort` to the flask import and `delete_expense as db_delete_expense` to the db import
- [x] 3. `app.py`: replace the stub with the POST route (login check → 404 → filter args → flash → redirect)
- [x] 4. **Checkpoint 1 dropped: on 2026-09-22 the developer said "stop after the completion of entire features", so the curl checks move into the Checkpoint 2 hand-off.** Originally: Give the developer curl commands to try the route: GET → 405; signed-out POST → 302 to `/login`; own id → 302 to `/profile?range=…`; same id again → 404; `999999` → 404. The developer runs them, since the main agent doesn't verify its own work. Continue after their go-ahead

**Checkpoint 2 — UI**
- [x] 5. `templates/_icons.html`: `trash()` macro
- [x] 6. `templates/profile.html`: empty `<th>` + per-row `row-delete-btn` cell
- [x] 7. `templates/profile.html`: `#delete-expense-modal` inside `{% if recent_expenses %}`
- [x] 8. `static/css/style.css`: 480px popup selector + `.btn-danger`
- [x] 9. `static/css/profile.css`: Step 9 block (column, button, popup layout, `.row-deleting` + keyframes) + reduced-motion line
- [x] 10. `static/js/main.js`: delete-popup IIFE
- [x] 11. **STOP — Checkpoint 2 (reached 2026-09-22; handed to the developer).** Hand the developer the spec's Manual Verification Guide (Validate)

**After Build (SDD steps 3–5)**
- [x] 12. `/test-feature 09-delete-button-feature` — 20/20 pass (2026-09-22; first run 19/20, a test-side bug: the signed-out test never signed out after registering, fixed in the test)
- [ ] 13. `/code-review-feature 09-delete-button-feature`
- [~] 14. PROGRESS.md route row + Step 9 section done 2026-09-23; committed + pushed as `930a95e` (without the code review, developer's call). Still pending: PR + merge. Original wording: route row `GET /expenses/<id>/delete — Stub — Step 9` → `POST /expenses/<id>/delete — Implemented — Step 9`, plus a Step 9 section; then commit, PR and merge (only after the developer asks)

## Explicitly out of scope
Same as spec §6: Edit (Step 8), Undo/soft delete, bulk delete, delete anywhere other than the `/profile` Recent Transactions rows, a no-JS fallback, CSRF, closing popups with Escape, changes to the Step 7 green highlight, and visual polish beyond existing tokens. Also not done here: a shared `openModal` helper (only two popups would use it) and a login-required decorator.

## Verification
- Spec §8 Acceptance Criteria (AC1–AC17), checked by hand through spec §9 Manual Verification Guide at Checkpoint 2.
- Spec §10 End-to-End Verification: `venv/bin/python -m pytest tests/test_09-delete-button-feature.py -v`, written by `/test-feature`, then the full `venv/bin/python -m pytest` as a regression check.
- `/code-review-feature 09-delete-button-feature` before any commit.
