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

- [x] `database/db.py`: add `monthly_budget REAL` and `notes TEXT` to the
      `users` table in `init_db()` + guarded `ALTER TABLE` for each
- [x] `database/db.py`: add `get_user_by_id(user_id)`
- [x] `database/db.py`: add `update_user(user_id, name, email,
      monthly_budget, notes, password=None)`
- [x] `database/db.py`: add `get_monthly_category_totals(user_id)`
      (current-calendar-month `GROUP BY category`)
- [x] `database/db.py`: add `get_recent_expenses(user_id, limit=5)`
- [x] `app.py`: import `flash`; rewrite `profile()` with the auth guard,
      `GET` display-data fetch, `POST` validation chain (mirroring
      `register`'s if/elif style), `update_user` call +
      `IntegrityError` catch, flash + redirect on success
- [x] `templates/base.html`: add "Profile" nav link inside the existing
      `{% if session.user_id %}` block; add toast markup driven by
      `get_flashed_messages`
- [x] `static/css/style.css`: `.toast` styles (top-right, success/error
      variants via `--accent`/`--danger`, fade transition), plus plain
      functional profile-section styles and a narrower `.modal-content`
      override for the verification popup (the shared `.modal` is sized
      for the video embed, so this one instance needs a max-width tweak)
- [x] `static/js/main.js`: toast auto-dismiss (~4s); verification-modal
      show/hide + resubmit flow, reusing the existing modal toggle pattern
- [x] `templates/profile.html`: full rewrite — settings form first
      (name/email/monthly_budget/notes/password fields, using
      `auth-card`/`form-group`/`form-input`/`btn-submit` conventions),
      then member-since line, monthly summary + category breakdown,
      recent-activity list, plus the verification-code modal markup
- [ ] Run through the spec's Manual Verification Guide end to end once all
      of the above is implemented — **left for the developer to do**, per
      CLAUDE.md's subagent policy: the main agent doesn't self-verify its
      own implementation (no `verify` subagent exists yet), so this box
      stays unchecked until you've actually run the guide yourself

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

## Revision — layout/content fix + spendly-ui-polish applied

The initial implementation above shipped correctly *for the design as
originally written* — single-column stacked cards, plain unstyled markup,
polish deferred. Two things then changed, in a follow-up fix (not a new
numbered spec — same feature, corrected):

1. **Layout**: single-column stacked cards → two-column grid (60/40),
   insights left (Overview, Recent activity, Notes), settings form right,
   collapsing to one column (insights first) on narrow screens. The
   "Page layout" bullet in the Design Plan above is superseded by this.
2. **Content**: a budget-vs-spent comparison (`₹X of ₹Y budget used`) was
   added to the Overview card, and the Notes field moved out of the
   settings form into its own standalone card (still submits through the
   same `#profile-form` via the HTML `form="profile-form"` attribute — no
   new route, no behavior change).
3. **`spendly-ui-polish` was invoked** on the finished page per its
   component table: editable-form-panel treatment on the settings card,
   content-panel on Overview, printed-receipt-strip on Recent activity,
   reference/notes-card on Notes. This was always the plan (see "Display
   content" bullet above) — it just hadn't actually been run yet when this
   file was first written.

Full context: this session's transcript, and the corrected plan the
developer approved for this fix.
