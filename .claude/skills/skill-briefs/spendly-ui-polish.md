# Brief for `skill-creator`: `spendly-ui-polish`

Paste this into the `skill-creator` plugin (enable it first — it's installed
but not in `enabledPlugins` yet) to generate
`.claude/skills/spendly-ui-polish/SKILL.md`.

Locked design reference: https://claude.ai/artifact/MJjs9Ed2iJcumWmXRyLDdw
("Spendly Paper Ledger" moodboard — versions 1-4, final version approved.)

## Skill identity

- **Name**: `spendly-ui-polish`
- **Description** (drives auto-invocation — keep it this narrow):
  > Applies Spendly's paper-and-receipt visual polish (torn edges, grain
  > texture, pins/tape, ruled-notebook cards, receipt strips) to an
  > already-implemented Flask template in this project. Use right after a
  > page's HTML structure, routes, and data are done, to restyle it. Do NOT
  > use for writing specs, planning, adding routes/fields/data, or touching
  > `app.py` / `database/db.py` logic.
- **Frontmatter**: do **not** set `disable-model-invocation` — the user
  wants hybrid behavior (auto-fires on a matching task, but can also be
  called by name). Omitting the field is what gives hybrid behavior; setting
  it to `true` would block auto-invocation entirely.

## Scope boundary (hard rule)

May edit:
- `static/css/style.css` and any new page-specific CSS file
- Template HTML markup — classes, decorative wrapper elements, existing
  field/label markup — never new `<form>` fields, new routes, or new data
- `static/js/main.js` — only minor visual interactions (hover states,
  toggle/settle animations), never business logic

Must never touch: `app.py`, `database/db.py`, route signatures, DB schema,
or session/auth logic. Must never invent new content — read the page's spec
only to know *what content patterns exist* (a stat panel? a list? a form?),
never as a source of visual rules.

## Design system (extracted from the approved prototype)

### Reuse existing tokens — do not replace

`static/css/style.css` already defines `--ink`, `--paper`, `--paper-card`,
`--accent` (`#1a472a` forest green), `--accent-light`, `--accent-2`
(`#c17f24` gold), `--accent-2-light`, `--danger`, `--border`, `--border-soft`,
`--radius-sm/md/lg`, and the `DM Serif Display` + `DM Sans` font pairing.
The paper-polish skill **extends** this token set — never overrides
`--accent`/`--accent-2`/`--danger`, and never invents a competing color
system.

### New tokens to add to `:root`

```css
--paper-stack-1: #e8e2d3;   /* stacked-sheet effect, layer 1 */
--paper-stack-2: #dcd4c0;   /* stacked-sheet effect, layer 2 */
--kraft: #e9dcc0;           /* index-card / kraft surfaces */
--kraft-line: #c9b98f;
--sticky: #f3e28f;          /* pastel yellow sticky note */
--sticky-mint: #cbe8d6;     /* pastel mint sticky note */
--ballpoint: #233a63;       /* handwritten annotation ink color */
--coral: #c25a3f;           /* "editable" affordance tag color */
--ruled-line: rgba(35, 58, 99, .14); /* notebook rule lines */

--font-type: 'Special Elite', 'Courier New', monospace;  /* printed/receipt text */
--font-hand: 'Caveat', cursive;                          /* handwritten annotations */
```

Add `Special Elite` and `Caveat` to the Google Fonts `<link>` in
`base.html` alongside the existing `DM Serif Display` / `DM Sans` request.

### Core textures (apply to every "paper" surface)

1. **Grain** — a tiled SVG-noise overlay, `mix-blend-mode: multiply`,
   opacity ~0.5, via a pseudo-element (`::after`, `position:absolute;
   inset:0; border-radius:inherit; pointer-events:none`) so it never blocks
   clicks/inputs:
   ```css
   --grain: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
   ```
2. **Crease/crumple** — two diagonal `linear-gradient`s (light/dark bands)
   as a second `background-image` layer, `background-blend-mode: multiply`,
   to fake fold highlights/shadows without any actual geometry distortion.
3. **Aged-paper filter** — `contrast(1.03) saturate(.93)` stacked onto the
   card's drop-shadow filter.

### Shape treatments — pick per component, don't mix on one element

| Component pattern | Treatment |
|---|---|
| Content panel (stat tiles, dashboard cards, "notes" cards) | Torn top edge only (`clip-path` jagged top, flat bottom) + tape **or** pin decoration (alternate, never both on one card) |
| Printed/transactional strip (expense list, receipt, any itemized total) | Torn **both** top and bottom (like a cut receipt) + `--font-type` (Special Elite) for rows/amounts, `font-variant-numeric: tabular-nums` |
| Editable form panel | Torn top edge, kraft background, small coral "✎ editable" tag next to the title, a small circular "hole-punch" dot near the top |
| Reference/notes card | Torn top edge + ruled-notebook line background (`repeating-linear-gradient` horizontal rules) + italic serif card title |
| Sticky note / reminder | **No torn edge** — clean rounded rectangle (`border-radius: 10px`), pastel background, own drop shadow, small tape strip, `--font-hand` (Caveat) content only |

Torn-top clip-path (reusable, jag amplitude in `px` so it stays constant
regardless of card height):
```css
clip-path: polygon(
  0% 6px, 7% 0px, 14% 9px, 21% 2px, 29% 7px, 36% 0px, 43% 8px, 50% 3px,
  57% 9px, 64% 1px, 71% 7px, 79% 0px, 86% 8px, 93% 2px, 100% 6px,
  100% 100%, 0% 100%
);
```
Mirror it for the bottom edge (using `calc(100% - Npx)`) when a component
needs both edges torn.

### Motion (subtle, one orchestrated pattern — don't add more)

- Cards fade + rotate-settle into place on load, staggered by a per-card
  `--delay`.
- On hover: rotate to `0deg`, lift `translateY(-6px)`, deepen the shadow.
  Respect `prefers-reduced-motion` (disable animation/transition, keep the
  resting state).

### Typography rules

- `DM Serif Display` italic → card/section titles only (`font-style: italic`),
  never body copy.
- `DM Sans` → all regular UI text, labels, buttons (unchanged from existing
  site usage).
- `Special Elite` → printed/receipt content only (amounts, itemized rows,
  small uppercase tag chips). Never headings, never buttons.
- `Caveat` → handwritten-feel microcopy only: sticky notes, small margin
  annotations/helper text under a form field. Never primary content, never
  anything load-bearing (it must always be a supplement to real text
  elsewhere, not the only copy of information).

## What the skill should NOT do

- Don't invent new page sections, fields, or copy — polish what the spec
  already implemented.
- Don't apply torn edges to sticky notes, or ruled-notebook lines to
  everything (it's specific to "reference/notes"-style cards).
- Don't touch `--accent`, `--accent-2`, `--danger`, or any existing token —
  extend the palette, don't replace it.
- Don't add a dependency, build step, or JS framework — vanilla CSS/HTML/JS
  only, matching the project's existing constraints.
