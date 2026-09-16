# Profile Page Redesign — Dashboard Structure + Paper Design System Fix

## Process note (added after Phase A landed)

Phase A (backend: `get_monthly_transaction_count`, derived `top_category`)
is implemented and verified, uncommitted. Before continuing to Phase B,
the developer flagged that this redesign skipped the project's own
Spec-Driven Development convention (`CLAUDE.md`'s SDD section) — it went
straight from an ad-hoc interview into this plan, with no
`.claude/specs/*.md` file, unlike the original Step 4 profile page
(`.claude/specs/04-profile-page.md`). The specific gap: a spec's required
**Manual Verification Guide** (beginner-friendly, step-by-step, exact UI
paths/commands/expected output) is missing — this plan's own
"Verification" section is terser implementation-checkpoint language, not
that.

**Decision**: write `.claude/specs/05-profile-page-redesign.md` via
`/create-spec` next, covering Phases B–F below (Phase A is already done
and doesn't need to be re-specified). Once that spec exists with its own
Acceptance Criteria + Manual Verification Guide, resume Phase B under it.
This plan file's Context/Decisions/technical-facts sections below feed
directly into that spec's interview — no need to re-derive them.

## Context

The Step 4 Profile page shipped as an editable settings page with some
read-only stats bolted on (`3695935`, PR open on `feature/profile-page`,
not yet merged). The developer supplied a reference screenshot of a
different, cleaner profile-page layout (read-only dashboard: avatar
header, 3 stat tiles, a Recent Transactions table, a By Category panel
with bars) and asked to restructure the current page to match that
*structure* — not its plain visual style, which will instead get
Spendly's paper design system.

Separately, the developer flagged a real flaw in the `spendly-ui-polish`
skill: it currently applies paper treatments card-by-card (torn edges,
tape, pins individually per card), copying the locked moodboard's look
too literally. The intent was always a single coherent metaphor — the
whole page reads as one crumpled sheet of paper, cards/tables on it look
hand-drawn, and tape/pins are reserved for the specific meaning "this is
physically stuck to the page for reference" (the way a real sticky note
gets pasted onto paper as a reminder) — not scattered as generic
decoration.

Two subagent research passes (codebase exploration + reference-image
analysis + side-by-side comparison) and a Plan agent's technical design
pass, plus a multi-round interview, produced the decisions below.

## Decisions locked in this session

| Question | Decision |
|---|---|
| Stat tiles (Total Spent / Transactions / Top Category) | Add all three — Transactions count needs a new `database/db.py` query; Top Category is derived in `app.py` from the already-sorted `category_totals` list, no new query needed. |
| Header | Redesign to avatar (initial letter) + name + email + member-since, read-only. Add an edit button in the **bottom-left** of the header card. |
| Edit-profile form (name/email/budget/password) | Moves **entirely** into a new modal, opened by the header's edit button, with a "crumpled paper unfolding" open animation. No longer inline on the page. |
| Notes textarea | Stays inline, own card, **not** in the modal. Its saved/displayed content renders in `--font-type` (Special Elite/typewriter). Becomes the page's one **sticky-note**-styled card (matches the developer's own "paste a reminder note" example). |
| Recent Transactions | Becomes a real `<table>`: Date / Description / Category (colored pill) / Amount. `description` is already a stored column and already returned by `get_recent_expenses` — template-only change. |
| By Category | Its own card (split out of the old combined Overview card), each row gets a horizontal bar proportional to `category_totals[0].total` (already DESC-sorted, no new backend value). |
| Budget-used line ("₹X of ₹Y budget used") | Becomes subtext under the Total Spent tile. |
| Design-system doc | Rewritten: global page-level crumpled-paper background (not per-card), hand-drawn card/table borders, tape/pin reserved for "stuck to the page for reference," sticky notes reserved for reminder content. |
| Visual implementation | **Not done in this pass.** A frontend-design mockup Artifact gets built and approved first (Phase F) — no real CSS for the new paper philosophy lands until the developer approves that mockup. |

## Verified technical facts (from the Plan agent's direct file reads)

- `database/db.py`: `get_monthly_category_totals(user_id)` scopes "this
  month" via `month_start = today.replace(day=1)`,
  `month_end = (month_start + timedelta(days=32)).replace(day=1)`,
  filtering `date >= month_start AND date < month_end`, already
  `ORDER BY total DESC`. The new transaction-count query copies this
  exact pattern. `get_recent_expenses(user_id, limit=5)` does `SELECT *`
  — `description` is already returned, just not rendered in the template.
- `app.py`'s `profile()` (lines ~115-236) has **three**
  `render_template("profile.html", ...)` call sites (GET success,
  validation-error branch, IntegrityError branch) — any new template
  variable needs to be added to all three, not just one.
- `static/js/main.js` (lines ~41-80) already has a working
  `#verification-modal` open/close IIFE — the new edit-profile modal's JS
  should be modeled directly on this pattern, not invented from scratch.
- `static/css/style.css` (lines ~325-379) already has shared
  `.modal`/`.modal-overlay`/`.modal-content`/`.modal-close` base classes
  used by the verification modal — reusable as-is for the new modal.
- The `form="profile-form"` attribute on the Notes textarea keeps
  associating to the form by id regardless of where the form sits in the
  DOM — moving the form into a modal doesn't break this, no extra
  plumbing needed.
- No avatar-circle pattern exists anywhere in the app today — this is
  genuinely new markup/CSS, not a reuse.
- No category→color mapping exists in `style.css` today;
  `expenses.category` is free-text, not an enum — needs a small,
  extensible set of CSS custom properties plus a fallback color for
  unrecognized categories.
- `--sticky` / `--sticky-mint` tokens are documented in
  `references/design-system.md` but were never added to `:root` in
  `style.css` — a known, already-tracked gap (`.claude/PROGRESS.md`),
  closed as part of Phase E/F.

## Tasks

### Phase A — Backend (`database/db.py` + `app.py`)
- [x] Add `get_monthly_transaction_count(user_id)` to `database/db.py`,
      copying `get_monthly_category_totals`'s month-scoping pattern:
      `SELECT COUNT(*) FROM expenses WHERE user_id = ? AND date >= ? AND date < ?`
- [x] In `app.py`, derive `top_category` from the existing
      `category_totals` list — `category_totals[0]["category"] if category_totals else None`
      — no new query.
- [x] Import `get_monthly_transaction_count` in `app.py`.
- [x] Call it once in `profile()`'s GET branch; compute `top_category`
      right after.
- [x] Add `transaction_count=` and `top_category=` to **all three**
      `render_template("profile.html", ...)` call sites.
- [x] Checkpoint: confirm both values render correctly before Phase B.
      Verified against seeded demo user (id 1, read-only check, no rows
      created): `transaction_count = 8`, `top_category = "Bills"` —
      matches `category_totals[0]`.

### Phase B — Template restructure (structure/content only, no paper polish yet)
- [ ] Header: avatar circle (`{{ name[0]|upper }}`), name, email, existing
      member-since line, edit button (bottom-left of the card, wired in
      Phase C). New CSS: `.profile-avatar`, `.profile-header-info`,
      `.profile-edit-btn`.
- [ ] New stat-tiles row: Total Spent (with budget-used subtext) /
      Transactions / Top Category (`or "—"` if empty). New CSS:
      `.profile-stats-row`, `.stat-tile`, `.stat-tile-label`,
      `.stat-tile-value`.
- [ ] Recent Transactions → real `<table class="transactions-table">`:
      Date / Description / Category (pill) / Amount, from
      `recent_expenses`.
- [ ] Add category→color CSS custom properties (seed categories +
      fallback) and a `.category-pill` class.
- [ ] New "By Category" card: bar width per row computed in the template
      as `row.total / category_totals[0].total * 100`, guarded by the
      existing empty-state check to avoid divide-by-zero.
- [ ] Remove superseded markup from the old combined Overview card
      (`.profile-summary-row`, `.profile-budget-line`, `.category-row`)
      once its pieces are redistributed into the tiles/By-Category card.
- [ ] Strip paper-card/torn-top/tape/pin classes from the cards being
      rebuilt this phase — plain structural wrapper for now (paper polish
      comes later, after mockup approval). Leave the Notes card's markup
      alone for now (it's touched in Phase D/F, not this phase).
- [ ] Checkpoint: show the restructured, unstyled page before Phase C.

### Phase C — Edit-profile modal
- [ ] New `#edit-profile-modal`, reusing the existing `.modal` /
      `.modal-overlay` / `.modal-content` / `.modal-close` classes.
- [ ] Move the entire existing `<form id="profile-form">` (name / email /
      monthly_budget / current_password / new_password / confirm_password
      + submit) into the modal, contents unchanged.
- [ ] Wire the header edit button to open the modal via a new IIFE in
      `static/js/main.js`, modeled on the existing `#verification-modal`
      IIFE, guarded with `if (!el) return;`.
- [ ] Add a "crumpled paper unfolding" open animation: CSS
      `@keyframes` (scaled-down/rotated → full size), no new dependency.
      Wrap in `@media (prefers-reduced-motion: reduce)`.
- [ ] Verify the email-change verification-code modal still triggers
      correctly from inside the new modal (it targets `#profile-form` by
      id, unaffected by the form's new DOM parent).
- [ ] Checkpoint: manually test modal open/close and one email-changing
      submit before Phase D.

### Phase D — Notes card (font fix now; sticky-note visual treatment deferred to Phase F)
- [ ] Add `font-family: var(--font-type);` to the notes textarea/display
      so saved notes content renders in the typewriter font.
- [ ] (Sticky-note visual restyle of this card happens in Phase F, after
      mockup approval — not yet.)

### Phase E — Design-system doc revision (doc-only, no CSS yet)
- [ ] Rewrite `.claude/skills/spendly-ui-polish/references/design-system.md`:
      replace the per-card treatment stacking with a single global
      page-level crumpled-paper background description.
- [ ] Redefine the default content-panel/table border as hand-drawn;
      note the concrete CSS recipe (SVG `feTurbulence`/`feDisplacementMap`
      filter vs. layered offset borders — no new dependency either way)
      gets picked during Phase F's mockup work, not guessed here.
- [ ] Rewrite the tape/pin section: restrict to the "physically stuck to
      the page for reference" affordance only.
- [ ] Rewrite the sticky-note section: restrict to reminder/"note to
      self" callout content — confirm the Notes card as the canonical
      example now that it's been decided as this page's sticky note.
- [ ] Add the missing `--sticky` / `--sticky-mint` tokens to `:root` in
      `style.css` (closes the tracked PROGRESS.md gap).
- [ ] Check `SKILL.md` for any remaining description of the old per-card
      philosophy and align it with the revised doc.

### Phase F — Design mockup for approval (next step after A–E land)
- [ ] Use the `frontend-design` skill to design the new global-background
      + hand-drawn-card + sparing tape/pin + Notes-as-sticky-note
      treatment, applied to the Phase B/C/D page structure.
- [ ] Publish it as an Artifact for the developer to review and approve.
- [ ] Only after approval: apply the approved visual design as real CSS
      via the (now-revised) `spendly-ui-polish` skill.

## Verification

- After Phase A: manually hit `/profile` and confirm `transaction_count`
  and `top_category` appear correctly for a seeded test user (clean up
  any seeded rows/users created only for this check, per this project's
  verification-hygiene rule). **Done** — see Phase A checklist.
- After Phase B: visually confirm the restructured page in the browser
  (`python app.py`, port 5001) matches the reference screenshot's
  *structure* (tile row, table columns, By Category bars) — no paper
  styling expected yet at this point.
- After Phase C: manually open/close the edit-profile modal, submit a
  name-only change, and submit an email change to confirm the
  verification-code flow still works from inside the modal.
- After Phase D: confirm saved Notes text visually renders in the
  typewriter font.
- Phase E is a doc-only change — verify by re-reading the updated
  `design-system.md` for internal consistency, no app behavior to test.
- Phase F's mockup is reviewed by the developer directly in the
  published Artifact — no code verification applicable at that stage.
