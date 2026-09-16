# Step 4 — Profile Page: Implementation Plan

Spec: `.claude/specs/04-profile-page.md`

## Design Plan

- **Auth guard**: an inline `if "user_id" not in session:` check at the top
  of `profile()`, not a decorator. This is the first protected route in
  the app — a `login_required` decorator would be the "correct" long-term
  shape, but with only one call site it's an abstraction the codebase
  doesn't need yet (CLAUDE.md: no unrequested abstractions). Revisit once
  a second route needs the same guard.
- **Toast**: rendered once in `base.html` from
  `get_flashed_messages(with_categories=True)` (a Jinja global, no import
  needed beyond `flash` in `app.py`). Fixed top-right position, two color
  variants (`--accent` for success, `--danger` for error), auto-dismiss
  ~4s via a `setTimeout` in `main.js` that fades and removes the element.
- **Verification popup**: reuses the existing `.modal`/`.modal-overlay`
  CSS and open/close pattern already in `main.js` for the "How it works"
  video modal — same show/hide mechanics, new content. JS flow: on form
  submit, compare the email input's current value to its original
  (page-load) value stored in a `data-original-email` attribute; if
  different and no code has been entered yet, prevent submission, open the
  modal, collect the code into a hidden `verification_code` input, then
  resubmit programmatically once confirmed.
- **Display content**: plain, functional markup reusing existing card-like
  classes (e.g. `.auth-card`) rather than inventing new visual language —
  visual polish is explicitly deferred to the `spendly-ui-polish` skill
  per the spec's Out of Scope.
- **Page layout**: settings form first (name/email/budget/notes/password),
  display content below (member-since, monthly summary + category
  breakdown, recent activity) — matches the existing auth-card-first
  convention on `login.html`/`register.html`.
- **No automated tests** — this project's established pattern (matching
  registration/login) is the spec's own Manual Verification Guide, not a
  pytest suite. `pytest`/`pytest-flask` stay unused for now.
- **DB layer**: four new functions in `database/db.py`
  (`get_user_by_id`, `update_user`, `get_monthly_category_totals`,
  `get_recent_expenses`), all following the existing
  `get_db()` → `try/finally: conn.close()` shape already used by
  `create_user`/`get_user_by_email`. Two new columns (`monthly_budget`,
  `notes`) added to `users` via `init_db()`, each with an idempotent
  guarded `ALTER TABLE ... ADD COLUMN` for pre-existing databases.

## Tasks

- [ ] `database/db.py`: add `monthly_budget REAL` and `notes TEXT` to the
      `users` table in `init_db()` + guarded `ALTER TABLE` for each
- [ ] `database/db.py`: add `get_user_by_id(user_id)`
- [ ] `database/db.py`: add `update_user(user_id, name, email,
      monthly_budget, notes, password=None)`
- [ ] `database/db.py`: add `get_monthly_category_totals(user_id)`
      (current-calendar-month `GROUP BY category`)
- [ ] `database/db.py`: add `get_recent_expenses(user_id, limit=5)`
- [ ] `app.py`: import `flash`; rewrite `profile()` with the auth guard,
      `GET` display-data fetch, `POST` validation chain (mirroring
      `register`'s if/elif style), `update_user` call +
      `IntegrityError` catch, flash + redirect on success
- [ ] `templates/base.html`: add "Profile" nav link inside the existing
      `{% if session.user_id %}` block; add toast markup driven by
      `get_flashed_messages`
- [ ] `static/css/style.css`: `.toast` styles (top-right, success/error
      variants via `--accent`/`--danger`, fade transition); no new modal
      CSS needed (reuses `.modal`)
- [ ] `static/js/main.js`: toast auto-dismiss (~4s); verification-modal
      show/hide + resubmit flow, reusing the existing modal toggle pattern
- [ ] `templates/profile.html`: full rewrite — settings form first
      (name/email/monthly_budget/notes/password fields, using
      `auth-card`/`form-group`/`form-input`/`btn-submit` conventions),
      then member-since line, monthly summary + category breakdown,
      recent-activity list, plus the verification-code modal markup
- [ ] Run through the spec's Manual Verification Guide end to end once all
      of the above is implemented

**Standing rule while working this checklist**: immediately after finishing
each task above, re-open this plan file and check its box — don't batch
updates to the end of the session or rely on memory. Re-reading this file
at any point must show exactly what's done and what's left, surviving a
compaction or a resumed session without re-deriving it from a diff.

## Explicitly out of scope

Matches the spec's Out of Scope: real OTP email verification, budget
threshold alerts/audit logging, the Dashboard page, full transaction
history/pagination, multi-month trends, and visual polish beyond existing
`style.css` tokens (that's `spendly-ui-polish`'s job, run separately once
this is functionally complete).

## Verification

Run the spec's own Manual Verification Guide
(`.claude/specs/04-profile-page.md`) end to end — all 13 numbered steps —
plus the End-to-End Verification walkthrough at the bottom of that spec.
