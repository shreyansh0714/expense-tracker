# Spendly UI-Polish Skill — Brief for skill-creator

## Context

The developer is building Spendly incrementally and keeps re-typing the same
"make this page look good" prompt after implementing each new page. They want
a reusable Claude Code **Skill** that only handles visual polish (spacing,
color, typography, decorative markup, minor JS interaction) on top of pages
whose structure/logic is already implemented per a spec + plan — never
structure, data, or business logic itself.

Two things surfaced during clarification that change the original ask:

1. **Invocation mode.** The original request said to add
   `disable-model-invocation: true` so the skill never auto-fires. Confirmed
   via the `claude-code-guide` agent that this field is real (SKILL.md-only,
   documented at code.claude.com/docs/en/skills.md) — but the user's actual
   answer was **Hybrid**: it should auto-fire when Claude recognizes a task is
   "polish this page's UI" (e.g. right after implementing the Profile page
   per its spec+plan), but also be callable by name on demand. `disable-model-invocation: true`
   would block auto-firing entirely, so it must be **omitted** — hybrid is
   just default skill behavior, achieved through a precisely scoped
   `description` field instead.
2. **Build path.** The user wants to run the official `skill-creator` plugin
   themselves (found installed at
   `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/`
   but not currently enabled — only `ponytail` is in `enabledPlugins`). So the
   deliverable here is a **written brief**, not a hand-authored `SKILL.md` —
   the user will paste this brief into skill-creator themselves.

Style direction (from clarification): combine "refine current design tokens"
with "bold modern fintech," plus a **literal paper/receipt motif** (torn
edges, paper-stack shadows, slight rotation, tape/pin accents) — a bigger
visual departure than a subtle texture. The user explicitly asked for a
**prototype first** so the skill's rules are locked to something they've
actually seen, not invented blind.

## What already exists (reused, not reinvented)

- `static/css/style.css` already defines the base design-token system:
  `--ink`, `--paper`, `--accent` (`#1a472a` forest green), `--accent-2`
  (`#c17f24` gold), `--radius-*`, `DM Serif Display` + `DM Sans`. The new
  paper/receipt motif extends these tokens — it does not replace them.
- `.claude/commands/create-spec.md` defines the spec format (10 `##`
  sections, no dedicated visual-requirements section) — confirms the skill
  should treat specs purely as "what content/fields exist," never as a
  styling source.
- No `.claude/skills/` directory exists yet in this project.

## Deliverables (in order)

1. **A living prototype**, published as a Claude Artifact — not real project
   files — showing the target look applied to representative Spendly UI
   pieces already in the app: stat cards (from the landing page's mock
   stats), an expense-row list, and a form panel (auth-style input/label
   pairs), all re-skinned with the paper/receipt/fintech direction, built on
   top of the existing `style.css` tokens (colors/type/radii above). Iterate
   with the user — upgrade/change the UI on their feedback — until locked.
2. **A written skill brief**, saved to
   `.claude/skill-briefs/spendly-ui-polish.md`, derived from the *approved*
   prototype, containing everything needed to run through `skill-creator`:
   - Proposed skill name (`spendly-ui-polish`, adjustable) and a
     `description` written narrowly enough to auto-fire only for "polish an
     already-implemented Spendly page's visual design" tasks, and explicitly
     exclude spec-writing, planning, routes, DB, and business logic.
   - Explicit note: **do not set** `disable-model-invocation` (hybrid mode).
   - Scope boundary: may edit `static/css/*.css`, template HTML markup
     (classes/decorative elements only, no new form fields/routes/data), and
     `static/js/main.js` for minor visual interactions only — mirrors the
     "CSS + HTML + minor JS polish" answer.
   - The concrete design-system rules extracted from the locked prototype:
     token extensions (paper-texture/shadow/rotation values as new CSS
     custom properties in `:root`), the paper/receipt motif's dos/don'ts,
     and how it composes with the existing `--accent`/`--accent-2` tokens.
   - Instruction that the skill reads the relevant spec/plan only to know
     *what content exists on the page* (e.g. "this page has a form" vs "this
     page has a list"), never as a source of visual rules.

## Follow-up (this planning session)

The prototype moodboard (https://claude.ai/artifact/MJjs9Ed2iJcumWmXRyLDdw) was
approved as the direction to move in. Two threads came up on top of it:

1. **Figma reference to fold in** (image read from `~/.claude/image-cache/...`
   with explicit one-off user permission — ask again each time this comes up,
   per the user's instruction). It shows a calmer "digital notepad" aesthetic,
   softer than the torn-receipt treatment already in the prototype:
   - Ruled-notebook lines as a background texture (thin horizontal rules),
     not the desk/linen texture
   - Main content card: clean white surface, rounded corners, soft drop
     shadow — **no torn/deckle edges, no tape, no pins**
   - Section titles set in serif italic (maps directly onto the existing
     `DM Serif Display` italic variant already loaded)
   - A small coral "✎ editable" pencil tag as a UI affordance label
   - Sticky notes: pastel yellow/mint/pink, rounded corners, gentle rotation,
     soft shadow, handwritten-style note content (maps onto `Caveat`, already
     in the prototype)
   - Reads as more refined/premium fintech, less skeuomorphic than the
     receipt-and-tape motif
   Plan: revise the prototype to blend this in — keep the receipt strip's
   printed/typewriter treatment (a real receipt is printed, not handwritten,
   so that distinction still holds), but replace the torn-edge/tape/pin
   treatment on the stat-tile, form, and swatch cards with this cleaner
   rounded-card + ruled-paper-background + soft-sticky-note language. Sticky
   notes (already used for the scope note) get the pastel/rounded treatment
   from the reference instead of the harsher pin+square look.
2. **Profile page content/sections** — confirmed **out of scope** for this
   plan. The user will run `/create-spec` separately for the Profile page
   (kept apart from the future, separately-planned Dashboard page). This plan
   stays focused on the UI-polish skill/design system only.

## Checklist

- [x] Revise the prototype artifact (same URL) to blend in the Figma
      reference: ruled-paper background option, clean rounded-corner cards
      with soft shadows (retiring torn/tape/pin on non-receipt cards),
      serif-italic section titles, softer pastel sticky notes
- [x] Review the revised prototype with the user until approved — went
      through two more rounds (restoring tape/pins, then adding torn edges +
      grain + crumple texture back in) before the user said to proceed
- [x] Extract the approved look into concrete design-system rules (tokens,
      motif dos/don'ts, when to use "printed receipt" vs "ruled notebook /
      sticky note" treatment)
- [x] Write `.claude/skill-briefs/spendly-ui-polish.md` with: skill name,
      scoped `description` (no `disable-model-invocation`), scope boundary
      (CSS + HTML + minor JS only), and the extracted design-system rules
- [ ] Report back to the user with the brief's location and next step (enable
      `skill-creator` plugin, paste the brief in; separately, run
      `/create-spec` for the Profile page's own content)

## Verification

- Manual: user opens the prototype Artifact in a browser and confirms it
  matches what they want (or requests revisions) before the brief is
  written.
- Manual: user reads `.claude/skill-briefs/spendly-ui-polish.md` and confirms
  the scope boundary and description text match their intent before running
  skill-creator.
- No automated tests apply — this task produces a prototype artifact and a
  markdown brief, not application code.
