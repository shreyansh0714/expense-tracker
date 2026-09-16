# Spec 05 — Profile Page Redesign (Dashboard Restructure + Edit Modal)

## Problem Statement

The Step 4 Profile page (merged in PR #5) reads as an editable settings
page with read-only stats folded in as an afterthought: a combined
"Overview" card mixes the total-spent figure, budget-used line, and
category breakdown together as plain text rows; "Recent activity" is a
flat list with no Description column; and the edit-profile form sits
permanently inline, competing for attention with the read-only content
above it.

The developer supplied a reference screenshot of a cleaner profile-page
layout — a read-only dashboard (avatar header, three stat tiles, a
proper Recent Transactions table, a By Category panel with proportional
bars) — and wants this page restructured to match that layout, with the
editable settings form relocated into a modal so the page reads primarily
as a dashboard, with editing as a secondary, deliberate action. The
backend values this requires (a current-month transaction count, the top
spending category) were already added in a prior session (see `app.py`
and `database/db.py` — both unchanged by this spec).

## Functional Requirements

**Display (read-only) content:**
- Header: an avatar circle showing the user's name's first letter
  (uppercase), their name, their email, and the existing
  "Member since `<month year>`" line — replacing the current
  `<h1>Your account</h1>` title.
- A row of three stat tiles:
  - **Total Spent** — this month's total (`monthly_total`), with a
    "₹X of ₹Y budget used" subtext beneath it when the user has a
    `monthly_budget` set (this replaces the old standalone budget-used
    line in the Overview card).
  - **Transactions** — this month's transaction count
    (`transaction_count`, already computed in `app.py`).
  - **Top Category** — the highest-spending category this month
    (`top_category`, already computed in `app.py`), or `"—"` when there's
    no data.
- **Recent Transactions**: a `<table>` with columns Date, Description,
  Category (rendered as a colored pill), and Amount — sourced from the
  existing `recent_expenses` data. `description` is already fetched by
  `get_recent_expenses`; it is simply not rendered today.
- **By Category**: its own card (split out of the old combined Overview
  card) — each row shows the category name and amount, with a horizontal
  bar whose width is proportional to the highest category's total
  (`category_totals[0].total`, already sorted descending).
- **Notes**: stays exactly where it is today — its own inline card, not
  moved into the modal. Its displayed/saved content renders in the
  `--font-type` (Special Elite / typewriter) font, which it does not
  today.

**Mutation (editable) content — unchanged from today, only relocated:**
- The existing edit-profile form (name, email, monthly budget, current
  password, new password, confirm password, plus the hidden
  `verification_code` field) moves in its entirety into a new modal
  dialog. No fields are added, removed, or changed in behavior — this is
  a relocation, not a redesign of the form itself.
- A new edit button, placed in the bottom-left corner of the header card,
  opens this modal.
- The modal opens with a "crumpled paper unfolding" animation (a scale/
  rotate CSS transition from a small, rotated state to full size),
  disabled under `prefers-reduced-motion: reduce`.
- The existing email-change verification-code modal (`#verification-modal`)
  must continue to work unchanged, including when triggered from inside
  the new edit-profile modal.
- The Notes textarea keeps submitting through `form="profile-form"` —
  this already works regardless of where the form sits in the DOM, so no
  JS change is needed for this specifically.

## APIs

No new routes. `GET/POST /profile` (`app.py:115`) is unchanged by this
spec — its backend logic, validation, and template context were already
finalized in a prior session (Phase A). This spec only changes what
`templates/profile.html` does with that existing context.

| Method | Path | Response |
|---|---|---|
| GET | `/profile` | Renders `profile.html` with the full context below |
| POST | `/profile` | Validates and updates via `update_user()`; redirects to `GET /profile` on success, re-renders with `error` on failure — behavior unchanged |

Template context already available (no new variables needed):
`name`, `email`, `monthly_budget`, `notes`, `member_since`,
`category_totals`, `monthly_total`, `transaction_count`, `top_category`,
`recent_expenses`, `original_email`, `budget_amount`, `error` (on
failure).

Existing form fields (unchanged): `name`, `email`, `monthly_budget`,
`notes`, `current_password`, `new_password`, `confirm_password`,
`verification_code`.

## Files and Interfaces Involved

- **`templates/profile.html`** — full restructure:
  - Header block: avatar + name + email + member-since + edit button.
  - New stat-tiles row (3 tiles).
  - Recent Transactions section becomes a `<table>`.
  - New standalone By Category card with bars.
  - Existing `<form id="profile-form">` moves into a new
    `#edit-profile-modal`, reusing the existing `.modal`/`.modal-overlay`/
    `.modal-content`/`.modal-close` structure (`style.css:325-379`) the
    same way `#verification-modal` does.
  - Notes card markup stays where it is; only its CSS changes.
- **`static/css/style.css`** — additions: `.profile-avatar`,
  `.profile-header-info`, `.profile-edit-btn`, `.profile-stats-row`,
  `.stat-tile` (+ `-label`/`-value`), `.transactions-table`,
  `.category-pill` (+ a small set of category→color custom properties in
  `:root`, plus one fallback color for categories outside that set, since
  `expenses.category` is free text, not an enum), `.category-bar-row`/
  `.category-bar`/`.category-bar-fill`, `#edit-profile-modal .modal-content`
  (its own `max-width` override, the same way `#verification-modal`
  narrows the base `.modal-content` at `style.css:800-802`), a crumple-
  open `@keyframes` + modifier class wrapped in
  `@media (prefers-reduced-motion: reduce)`, and
  `font-family: var(--font-type);` added to the notes textarea/display
  rule. Removes superseded selectors: `.profile-summary-row`,
  `.profile-budget-line`, `.category-row` (old combined Overview rows).
- **`static/js/main.js`** — new IIFE for `#edit-profile-modal`, modeled
  directly on the existing `#verification-modal` IIFE (`main.js:41-80`):
  guard on missing elements, `openModal()`/`closeModal()` toggling
  `hidden`, wired to the new edit button and to `[data-modal-close]`
  elements inside it.
- **`app.py`, `database/db.py`** — no changes. Both already carry this
  spec's required backend values from the prior Phase A commit.

## Constraints

- Reuse the existing `.modal`/`.modal-overlay`/`.modal-content`/
  `.modal-close` CSS classes and the `#verification-modal` JS pattern —
  do not build a second modal system.
- Category pill colors must be new CSS custom properties added to
  `:root`, never hardcoded hex values, and must include a fallback color
  for any category string outside the known seed set (Food, Transport,
  Bills, Health, Entertainment, Shopping, Other) since categories are
  free text.
- The crumple-open modal animation must be pure CSS (`@keyframes` +
  class toggle from JS), no new dependency, and must respect
  `prefers-reduced-motion: reduce`.
- No changes to `app.py` route logic, `database/db.py`, DB schema, or
  session/auth logic — this spec is templates/CSS/JS only.
- No paper-texture visual treatment (torn edges, grain, tape, pins,
  sticky-note styling) is applied as part of this spec — see Out of
  Scope. Cards built in this spec should be structurally correct but
  visually plain (existing `.auth-card` base styling is fine as a
  placeholder).
- Follow existing code style: kebab-case CSS classes, `url_for()` for any
  internal links, 4-space indent in templates, vanilla JS wrapped in an
  IIFE guarded with `if (!el) return;`.

## Out of Scope

- **The global paper-design-system overhaul** (page-level crumpled-paper
  background, hand-drawn card/table borders, tape/pin decorations, and
  the Notes card's sticky-note styling) — tracked separately as Phase E
  (design-system.md doc rewrite) and Phase F (frontend-design mockup +
  developer approval + `spendly-ui-polish` implementation) in
  `.claude/plans/05-profile-page-redesign.md`. Nothing in this spec
  should apply torn-edge/tape/pin/sticky-note CSS classes.
- **Budget threshold alerts and auto-calculated suggested budgets** —
  explicitly deferred to a future Dashboard spec per
  `.claude/PROGRESS.md`'s Future Features table; developer confirmed in
  this session's interview that this page should carry no preview or
  cue for either.
- **Any new editable field** beyond the existing name/email/budget/
  password/notes set — developer confirmed no new mutation surface in
  this redesign.
- **Avatar photo upload** — the new avatar is a static initial-letter
  circle only; upload capability stays out of scope per the original
  Step 4 spec.
- **Real OTP email verification, account deletion, full transaction
  history/pagination, multi-month trends** — already out of scope per
  `.claude/specs/04-profile-page.md`, unchanged here.

## Edge Cases and Error Handling

- User has zero expenses this month → `transaction_count` is `0`,
  `top_category` is `None` → Top Category tile shows `"—"`; By Category
  card and Recent Transactions table fall back to their existing
  empty-state messages; no divide-by-zero when computing bar widths
  (guard on `category_totals` being non-empty before dividing by
  `category_totals[0].total`).
- `name` is always non-empty by the time it reaches the template (POST
  validation requires it), but the avatar-initial expression should
  still guard defensively (`{{ name[0]|upper if name else "?" }}`).
- A category string outside the known seed set (user-entered free text)
  → category pill falls back to a default color rather than rendering
  unstyled or breaking.
- Long description/category text in a table cell → CSS handles overflow
  gracefully (e.g. `text-overflow: ellipsis`), does not break the table
  layout.
- The email-change verification-code modal must still correctly open and
  function while the edit-profile modal is open behind it (nested modal
  display) — both toggle independently via their own `hidden` state.
- No monthly budget set (`monthly_budget` is `None`) → Total Spent tile
  shows only the total, no budget-used subtext (existing conditional
  logic, unchanged).

## Acceptance Criteria

- [ ] Profile header shows an avatar circle (first-letter initial), name,
      email, and "Member since" date — replacing "Your account".
- [ ] A row of 3 stat tiles shows Total Spent (with budget-used subtext
      when a budget is set), Transactions count, and Top Category
      (or "—" when empty).
- [ ] Recent Transactions renders as a table with Date, Description,
      Category (colored pill), and Amount columns.
- [ ] A separate By Category card shows each category's amount with a
      bar proportional to the highest category total.
- [ ] The edit-profile form (name/email/budget/password) is fully inside
      a modal, no longer inline on the page.
- [ ] An edit button in the bottom-left of the header card opens that
      modal.
- [ ] The modal opens with a crumpled-paper-unfolding animation, disabled
      under `prefers-reduced-motion: reduce`.
- [ ] The email-change verification-code modal still opens and works
      correctly when triggered from inside the edit-profile modal.
- [ ] The Notes card stays inline (not in the modal), and its content
      displays in the typewriter (`--font-type`) font.
- [ ] All existing POST validation/behavior (field rules, email
      verification bypass code, duplicate-email handling) continues to
      work unchanged.
- [ ] No changes to `app.py` or `database/db.py` beyond what Phase A
      already added.

## Manual Verification Guide

**Setup (do this once):** open a terminal in the project folder, run
`source venv/bin/activate` then `python app.py`. Open
`http://localhost:5001/login` in your browser. Log in with the seeded
demo account: email `demo@spendly.com`, password `demo123`. You should
land on `/profile`.

1. **Header redesign**
   - Look at the top card on the profile page.
   - Expected: a circular avatar with a single letter inside it, the
     name "Demo User" (or your account's name), the email
     `demo@spendly.com`, and a "Member since" line — no "Your account"
     heading text anywhere.

2. **Stat tiles**
   - Look at the row of 3 boxes directly below the header.
   - Expected: three tiles labeled "Total Spent", "Transactions", and
     "Top Category", each showing a value. If the demo account has
     expenses logged this month, Total Spent should be a rupee amount,
     Transactions should be a number greater than 0, and Top Category
     should be a category name (not "—").

3. **Budget-used subtext**
   - If the demo account has no monthly budget set, skip this step.
   - If it does, look directly under the Total Spent tile's value.
   - Expected: a smaller line reading something like
     "₹X of ₹Y budget used".

4. **Recent Transactions table**
   - Find the "Recent Transactions" section.
   - Expected: an actual table with 4 column headers — Date,
     Description, Category, Amount. The Category column should show
     colored pill/badge shapes, not plain text.

5. **By Category card**
   - Find the "By Category" section (should be its own card, separate
     from the stat tiles).
   - Expected: one row per category, each with a horizontal bar. The
     category with the highest amount should have the longest/fullest
     bar.

6. **Edit button opens the modal**
   - Look at the bottom-left corner of the header card and click the
     edit button there.
   - Expected: a modal dialog appears on top of the page, with a
     noticeable "unfolding" animation as it opens (not an instant
     pop-in). The modal should contain the name/email/budget/password
     fields.

7. **Reduced motion respected**
   - On macOS: System Settings → Accessibility → Display → turn on
     "Reduce motion". Reload the profile page and click the edit button
     again.
   - Expected: the modal still opens, but without the unfolding
     animation (appears instantly or with a simple fade).

8. **Email-change verification still works from inside the modal**
   - With the edit modal open, change the Email field to a different
     address and click Save (or the form's submit button).
   - Expected: a second modal (the verification-code popup) appears
     asking for a code, without the edit modal breaking or closing
     unexpectedly.
   - In your terminal, run: `export PROFILE_EMAIL_BYPASS_CODE=123456`
     (then restart `python app.py` so it picks up the env var), enter
     `123456` in the verification popup, and confirm.
   - Expected: the page reloads with a "Profile updated." success
     message, and the header now shows the new email.

9. **Notes stays outside the modal, renders in typewriter font**
   - Close any open modal. Find the "Notes" card on the main page (not
     inside the modal).
   - Type something into it and save (submit button is inside the edit
     modal via the `form="profile-form"` attribute — you may need to
     open the modal, click its submit button, with the notes text
     already typed into the visible Notes card first).
   - Expected: after the page reloads, the saved notes text visually
     looks different from the rest of the page's font — a typewriter-
     style monospace look (this is the `--font-type` / "Special Elite"
     font).

10. **No backend files changed**
    - Run `git diff --stat main -- app.py database/db.py` in your
      terminal (once this spec's implementation is committed).
    - Expected: no output (empty) — confirming neither file changed
      beyond the already-committed Phase A backend work.

## End-to-End Verification

Starting from a fresh browser session: log in as `demo@spendly.com` /
`demo123`, land on `/profile`, and confirm the dashboard renders (header
avatar/name/email, 3 stat tiles with real values, a Recent Transactions
table with visible Description text and colored category pills, and a By
Category card with proportional bars). Click the header's edit button —
confirm the modal opens with the unfolding animation and contains the
full settings form. Change the name field only and submit — confirm the
modal closes, the page reloads with a "Profile updated." toast, and the
header now shows the new name. Reopen the modal, change the email field,
submit, and complete the verification-code flow (bypass code from
`PROFILE_EMAIL_BYPASS_CODE`) — confirm success. Finally, with the app
stopped, run:

```bash
sqlite3 database.db "SELECT name, email FROM users WHERE email = '<the new email you set>';"
```

Expected: one row, with `name` matching what you typed and `email`
matching the new address — confirming the modal-relocated form still
persists changes identically to before this redesign.
