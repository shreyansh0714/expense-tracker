# Implementation Plan — Spec 05: Profile Page Redesign (Dashboard + Edit Modal)

Paired with `.claude/specs/05-profile-page-redesign.md` per this
project's spec/plan pairing convention. Supersedes this file's earlier
ad-hoc 6-phase draft (kept, for now, in the git history of this file) —
that draft's Phase A (backend: `get_monthly_transaction_count`, derived
`top_category`) is already implemented, verified, and committed
(`5cf439c` on `feature/profile-page-redesign`). This plan covers exactly
what the spec scopes: the dashboard restructure, the edit-profile modal,
and the notes font-fix. Phase E (design-system doc rewrite) and Phase F
(mockup + paper-visual implementation) stay out of this plan, tracked
separately, per the spec's Out of Scope.

Decisions confirmed this session, on top of the spec:
- **No automated tests this pass.** Gate 2 (pytest) and the full Gate 1
  manual walkthrough are both deferred to a later, consolidated
  verification pass once Phase E/F's visual work also lands — not run
  incrementally after this implementation.
- **Category pill colors: minimal/placeholder now.** Reuse existing
  `--accent-light`/`--accent-2-light`/`--border-soft`-style tokens
  rotated across categories via CSS attribute selectors, not a new
  7-color palette — real palette work happens in Phase F.

## Design Plan

**Header restructure.** No existing avatar-circle pattern exists
anywhere in the app (confirmed by exploration) — this is genuinely new
markup: a `.profile-avatar` div showing `{{ name[0]|upper if name else "?" }}`,
sibling to a `.profile-header-info` block (name, email, existing
member-since line). The edit button becomes a real
`<button type="button" id="open-edit-profile">` positioned bottom-left
via a simple two-row flex layout on `.profile-header` (avatar+info row,
then the button on its own row with `align-self: flex-start`) — no
absolute positioning needed, keeps it simple.

**Stat tiles.** Three `.stat-tile` divs in a `.profile-stats-row` grid,
reusing the existing `.auth-card` base class per the spec's constraint
that this phase stays "structurally correct but visually plain." Total
Spent tile gets an extra subtext line for the budget-used comparison,
shown only when `budget_amount is not none` (same conditional the
current template already uses).

**Recent Transactions table.** Replace the `.activity-row` flex-list with
a real `<table class="transactions-table">`. Category pill color is
handled with a `data-category="{{ expense.category|lower }}"` attribute
plus CSS attribute selectors — this is the simplest correct way to
express "known categories get their own tint, anything else falls back"
in pure CSS: a base `.category-pill` rule sets the fallback color, and
`[data-category="food"]` etc. override it only for the known seed set.
No Jinja category→color mapping logic needed in the template, no JS.

**By Category bars.** Bar width computed directly in Jinja —
`style="width: {{ (row.total / category_totals[0].total * 100) | round(1) }}%"`
— guarded by the template's existing `{% if category_totals %}` check
(already prevents the divide-by-zero case). Server-rendered, no JS.

**Edit-profile modal.** Move the existing `<form id="profile-form">`
(unchanged internals) into a new `#edit-profile-modal`, structurally
identical to `#verification-modal` (`.modal` > `.modal-overlay` +
`.modal-content` + `.modal-close`/`[data-modal-close]`). The new
`static/js/main.js` IIFE is a direct structural copy of the existing
`#verification-modal` IIFE (`main.js:41-80`) — same guard/openModal/
closeModal/`[data-modal-close]` wiring — just triggered by the new edit
button's `click` instead of a form-submit condition. The `form="profile-form"`
attribute on the Notes textarea needs no change; HTML form association
works by id regardless of DOM nesting.

**Crumple-open animation.** A CSS `@keyframes crumple-open` (scale+rotate
from ~0.3/-8deg to 1/0deg) applied via a `.modal-content.opening` class
that JS adds on open and removes after the animation completes (matching
duration via a JS timeout, the standard dependency-free way to let a CSS
animation "replay" reliably across browsers). Wrapped in
`@media (prefers-reduced-motion: reduce) { .modal-content.opening { animation: none; } }`.

**Notes font-fix.** One-line CSS addition —
`font-family: var(--font-type);` on the existing notes textarea rule.

**Verification.** No automated tests are written in this pass (see
decision above). The spec's own Acceptance Criteria, Manual Verification
Guide, and End-to-End Verification sections remain the source of truth
for verifying this work — to be run in full at the later consolidated
pass, not restated here.

## Tasks

- [x] Header restructure: avatar circle, name, email, member-since, edit
      button — `templates/profile.html` + new CSS (`.profile-avatar`,
      `.profile-header-info`, `.profile-edit-btn`) in `style.css`.
- [x] Stat tiles row (Total Spent + budget-used subtext, Transactions,
      Top Category) — template + `.profile-stats-row`/`.stat-tile`
      (`-label`/`-value`) CSS.
- [x] Recent Transactions table (Date/Description/Category pill/Amount)
      — template + `.transactions-table`/`.category-pill` CSS
      (attribute-selector based, placeholder tokens).
- [x] By Category card with proportional bars — template +
      `.category-bar-row`/`.category-bar`/`.category-bar-fill` CSS.
- [x] Remove superseded Overview-card markup and CSS
      (`.profile-summary-row`, `.profile-budget-line`, old
      `.category-row`) once their content is redistributed above.
- [x] **Checkpoint:** show the restructured (plain-styled) dashboard in
      the browser before starting the modal work. (Verified via Flask
      test client — 200 status, all markers present. Live browser
      screenshot unavailable this session — Playwright's browser
      profile was locked by another process.)
- [x] New `#edit-profile-modal` markup — move the existing
      `<form id="profile-form">` into it, reusing `.modal`/
      `.modal-overlay`/`.modal-content`/`.modal-close`, with its own
      `.modal-content` `max-width` override.
- [x] New `static/js/main.js` IIFE for the edit-profile modal
      (open/close), wired to the new edit button, modeled on the
      `#verification-modal` IIFE.
- [x] Crumple-open animation CSS (`@keyframes` + `.opening` class) with
      `prefers-reduced-motion` guard.
- [x] Verified by code inspection: the email-change verification-code
      modal targets `#profile-form`/`#email`/`#verification-modal` by
      id, which resolve identically regardless of `#profile-form`'s new
      DOM nesting inside `#edit-profile-modal`; both modals share
      `z-index: 200` and `#verification-modal` is later in DOM order so
      it paints on top when both are open. **Not live-browser tested**
      this session (Playwright locked) — flagging for the deferred
      consolidated verification pass.
- [~] **Checkpoint:** manually test modal open/close, the animation, and
      reduced-motion behavior — **not done this session**, no working
      browser available. Deferred to the consolidated verification pass.
- [x] Add `font-family: var(--font-type);` to the notes textarea CSS
      rule.
- [x] **Checkpoint:** self-sanity pass against the spec's Acceptance
      Criteria done by code inspection + Flask test-client checks (see
      report). Full Gate 1/Gate 2 verification remains the deferred,
      later consolidated pass.

**Standing rule for whoever implements this plan:** immediately after
finishing each task, re-open this file and check its box. Don't batch
updates to the end of a session, and don't rely on memory — this file
has to stay accurate *while the work is in progress* to survive a
mid-session compaction or a resumed session later.

## Explicitly out of scope

Mirrors `.claude/specs/05-profile-page-redesign.md`'s Out of Scope:
- The global paper-design-system overhaul (crumpled background,
  hand-drawn borders, tape/pin, Notes-card sticky-note styling) — Phase
  E/F, separate work.
- Budget threshold alerts / auto-calculated suggested budget previews.
- Any new editable field beyond the existing set.
- Avatar photo upload.
- Real OTP email verification, account deletion, full transaction
  history/pagination, multi-month trends.
- Automated tests (this pass) — deferred per this session's decision
  above, not because the spec excludes them.

## Verification

See `.claude/specs/05-profile-page-redesign.md`'s Acceptance Criteria,
Manual Verification Guide, and End-to-End Verification sections — not
restated here. Per this session's decision, the full run-through of
those sections is deferred to a later consolidated pass alongside Phase
E/F, not performed immediately after this implementation.
