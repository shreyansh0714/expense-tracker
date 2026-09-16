# Spendly paper-and-receipt design system

Source of truth for everything `spendly-ui-polish` applies. Locked from the
approved prototype: https://claude.ai/artifact/MJjs9Ed2iJcumWmXRyLDdw
("Spendly Paper Ledger" moodboard, final version).

## Reuse existing tokens — never replace them

`static/css/style.css` already defines `--ink`, `--paper`, `--paper-card`,
`--accent` (`#1a472a` forest green), `--accent-light`, `--accent-2`
(`#c17f24` gold), `--accent-2-light`, `--danger`, `--border`,
`--border-soft`, `--radius-sm/md/lg`, and the `DM Serif Display` +
`DM Sans` font pairing. This system extends that set — it never overrides
`--accent`, `--accent-2`, or `--danger`, and never introduces a second,
competing color system.

## New tokens to add to `:root`

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
`base.html` alongside the existing `DM Serif Display` / `DM Sans` request,
the first time either font is needed on a page. Don't add fonts nothing on
the page uses.

## Core textures — apply to every "paper" surface

1. **Grain** — a tiled SVG-noise overlay, `mix-blend-mode: multiply`,
   opacity ~0.5, via a pseudo-element so it never blocks clicks/inputs:
   ```css
   --grain: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
   ```
   ```css
   .sheet::after {
     content: "";
     position: absolute;
     inset: 0;
     border-radius: inherit;
     background-image: var(--grain);
     background-size: 140px 140px;
     mix-blend-mode: multiply;
     opacity: .5;
     pointer-events: none;
   }
   ```
2. **Crease/crumple** — two diagonal `linear-gradient`s (light/dark bands)
   as a second `background-image` layer, `background-blend-mode: multiply`,
   faking fold highlights/shadows with no actual geometry distortion:
   ```css
   --crease:
     linear-gradient(114deg, rgba(255,255,255,.55) 0%, transparent 9%, transparent 21%, rgba(20,15,8,.07) 27%, transparent 35%, transparent 58%, rgba(255,255,255,.4) 65%, transparent 74%),
     linear-gradient(32deg, transparent 38%, rgba(20,15,8,.05) 47%, transparent 55%, transparent 80%, rgba(255,255,255,.3) 87%, transparent 95%);
   ```
   Apply as `background-image: var(--crease);` with
   `background-blend-mode: multiply, multiply;` alongside the surface's own
   `background-color` (never the `background:` shorthand, which would wipe
   the image out).
3. **Aged-paper filter** — stack `contrast(1.03) saturate(.93)` onto
   whatever `filter: drop-shadow(...)` the card already uses for its lift.

## Shape treatments — pick one per component, never mix on one element

| Component pattern | Treatment |
|---|---|
| Content panel (stat tiles, dashboard cards) | Torn top edge only (jagged top, flat bottom) + tape **or** pin decoration — alternate which, never both on one card |
| Printed/transactional strip (expense list, receipt, any itemized total) | Torn **both** top and bottom (like a cut receipt) + `--font-type` for rows/amounts, `font-variant-numeric: tabular-nums` |
| Editable form panel | Torn top edge, kraft background (`--kraft`), small coral "✎ editable" tag next to the title, a small circular "hole-punch" dot near the top |
| Reference/notes card | Torn top edge + ruled-notebook line background + italic serif card title |
| Sticky note / reminder | **No torn edge** — clean rounded rectangle (`border-radius: 10px`), pastel background (`--sticky` / `--sticky-mint`), own drop shadow, small tape strip, `--font-hand` content only |

**Torn-top clip-path** (jag amplitude in `px`, not `%`, so it stays
constant regardless of card height):
```css
clip-path: polygon(
  0% 6px, 7% 0px, 14% 9px, 21% 2px, 29% 7px, 36% 0px, 43% 8px, 50% 3px,
  57% 9px, 64% 1px, 71% 7px, 79% 0px, 86% 8px, 93% 2px, 100% 6px,
  100% 100%, 0% 100%
);
```
For **torn-both** (receipt-style), mirror the same jag onto the bottom edge
using `calc(100% - Npx)` for the y-values instead of `100%`.

**Ruled-notebook background** (for reference/notes cards):
```css
background-image: repeating-linear-gradient(to bottom, transparent 0 27px, var(--ruled-line) 27px 28px);
```

**Tape** and **pin** decorations sit just above the card's top edge
(`top: -8px` to `-11px`, absolutely positioned), gold-toned
(`var(--gold)`/`var(--gold-dark)`), and rotate a few degrees off-axis for a
hand-placed feel. Never put both on the same card — pick one.

**Paper-stack depth** (optional, for extra dimension behind a torn card):
two `::before`/`::after` pseudo-elements on the card's wrapper, offset a
few px and rotated slightly more/less than the card itself, colored
`--paper-stack-1` / `--paper-stack-2`, sitting behind it — mimics a couple
of sheets underneath the top one. Skip this for sticky notes.

## Motion — one orchestrated pattern, don't add more

- Cards fade + rotate-settle into place on load, staggered by a per-card
  delay (a CSS custom property like `--delay` read by `animation-delay`).
- On hover: rotate to `0deg`, lift `translateY(-6px)`, deepen the shadow
  slightly.
- Respect `prefers-reduced-motion: reduce` — disable the animation and
  transition durations, keep the resting state.

## Typography rules

- `DM Serif Display` italic → card/section titles only. Never body copy.
- `DM Sans` → all regular UI text, labels, buttons — unchanged from
  existing site usage.
- `Special Elite` → printed/receipt content only (amounts, itemized rows,
  small uppercase tag chips). Never headings, never buttons.
- `Caveat` → handwritten-feel microcopy only: sticky notes, small margin
  annotations or helper text under a form field. Never primary content —
  it must always supplement real text elsewhere, never be the only copy of
  a piece of information (accessibility: script fonts are harder to read).

## What this skill should never do

- Invent new page sections, fields, or copy — polish what's already there.
- Put torn edges on sticky notes, or ruled-notebook lines on anything that
  isn't a reference/notes card.
- Touch `--accent`, `--accent-2`, `--danger`, or any existing token —
  extend the palette, never replace a value already in use elsewhere.
- Add a dependency, build step, or JS framework — vanilla CSS/HTML/JS only.
- **Copy the mockup's look, never its words.** The paper-ledger moodboard
  linked at the top of this file is a design reference, not a content
  source — its text is fake, written only to make the mockup look
  realistic. Two concrete examples from that moodboard that are NOT real
  and must NEVER be copied onto an actual page: the caption "auto-
  calculated from last 3 months" under the mockup's budget field (no such
  calculation exists in this app), and the two "Pinned" sticky notes
  ("Beautify only — CSS + markup polish...", "Read the spec first. Style
  second.") — those are notes-to-self about building this skill, not
  content a real user should ever see. When a mockup shows example text,
  pull colors/spacing/typography/treatment from it, and pull the *real*
  page's actual content/copy from the spec or the page itself — never
  from the mockup's placeholder text.
