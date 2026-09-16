# Spendly paper-and-receipt design system

Source of truth for everything `spendly-ui-polish` applies. Originally
locked from the approved prototype:
https://claude.ai/artifact/MJjs9Ed2iJcumWmXRyLDdw ("Spendly Paper
Ledger" moodboard). **Revised 2026-09-17** after the developer flagged a
real mistake in the first version of this system: it applied paper
textures *per card* (each card independently got its own grain, crease,
torn edge, and often a tape or pin), so a page read as a small pile of
separately-decorated paper scraps sitting next to each other — closer to
the moodboard's literal look than to the actual intent. See "Page-level
foundation" below for the fix. This revision is doc-only — the CSS/
markup for pages already polished under the old system (none yet
shipped) gets updated in the next implementation pass, not retroactively
by this edit.

## Reuse existing tokens — never replace them

`static/css/style.css` already defines `--ink`, `--paper`, `--paper-card`,
`--accent` (`#1a472a` forest green), `--accent-light`, `--accent-2`
(`#c17f24` gold), `--accent-2-light`, `--danger`, `--border`,
`--border-soft`, `--radius-sm/md/lg`, and the `DM Serif Display` +
`DM Sans` font pairing. This system extends that set — it never overrides
`--accent`, `--accent-2`, or `--danger`, and never introduces a second,
competing color system.

## Design system tokens (all present in `:root`)

```css
--paper-stack-1: #e8e2d3;   /* currently unused — the "paper-stack depth"
                                technique it supported was for extra
                                dimension behind a torn card; torn edges
                                on individual cards are retired by this
                                revision. Tracked in PROGRESS.md for
                                Phase F cleanup, not removed here. */
--paper-stack-2: #dcd4c0;   /* same as above */
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

## Page-level foundation — one sheet, not a stack of separately-decorated cards

This is the philosophy fix. Previously, grain + crease + the aged-paper
filter were applied per card, and each card could also get its own torn
edge plus a tape or pin. The result was several small, independently
"papered" rectangles next to each other — a stack, not a sheet. The
actual intent is simpler and more literal: **the entire page is one
large piece of paper.** Apply grain, crease, and the aged-paper filter
**once, to the page background**, not per card:

```css
body {
    background-color: var(--paper);
    background-image: var(--crease);
    background-blend-mode: multiply;
    position: relative;
    filter: contrast(1.03) saturate(.93);
}

body::after {
    content: "";
    position: fixed;
    inset: 0;
    background-image: var(--grain);
    background-size: 140px 140px;
    mix-blend-mode: multiply;
    opacity: .5;
    pointer-events: none;
    z-index: 1;
}
```

(`pointer-events: none` on the grain overlay keeps it from ever blocking
clicks/inputs.) Cards sitting on top of this background read as things
*drawn on* the sheet — plain content regions with a hand-drawn border
(below), not their own separately-textured paper scraps. No individual
card should carry its own `--grain`/`--crease` background or its own
`contrast()/saturate()` filter stack anymore — that texture now lives in
exactly one place.

## Card/table treatment — hand-drawn, not torn-edge stacking

Cards and tables no longer get a torn-edge `clip-path` — that was the
per-card "paper scrap" signature this revision retires. Instead, a card
reads as something *drawn on* the page: a hand-drawn (slightly
irregular, sketchy) border in place of a crisp, machine-perfect
rectangle.

**Concrete recipe: not locked yet — pick one during the Phase F mockup
pass, don't guess here.** Two candidate techniques:
1. An SVG `feTurbulence` + `feDisplacementMap` filter distorting a clean
   rectangular border/outline into a hand-drawn-looking one.
2. Two or three layered elements at slightly different `border-radius`
   values and a few degrees of `rotate`, stacked so their edges peek out
   unevenly from behind each other — cheaper than an SVG filter, no
   filter performance cost, but reads as less convincingly "drawn."

Whichever gets picked applies uniformly to every content panel and table
in this system (stat tiles, the transactions table, the by-category
card, etc.) — there's no longer a "torn top" vs. "torn both" vs. "kraft"
distinction between component types. One hand-drawn border style, used
everywhere a card needs an edge.

## Shape treatments — revised table

| Component pattern | Treatment |
|---|---|
| Content panel (stat tiles, dashboard cards, tables) | Hand-drawn border (see above). No torn edge, no per-card grain/crease/filter — those now live at the page level only. |
| Editable form panel | Same hand-drawn border. No kraft background and no coral "editable" tag — those were per-card-paper-scrap signifiers, retired along with torn edges. A form is just a card with a hand-drawn border like any other. |
| Reference/notes card | Hand-drawn border + ruled-notebook line background + italic serif card title. The ruled-line texture is the one per-card interior texture that survives this revision — it signals "this is a page from a notebook," which is a real, specific meaning, not generic paper decoration. |
| Reminder callout (sticky note) | See "Sticky note" below — the one place tape/pin styling still applies. |

## Tape and pin — reserved for "this is physically stuck to the page," not decoration

Previously tape/pin appeared on most cards as a generic decorative
flourish (alternating tape-or-pin per card, per the old table). That's
retired. Tape and pin now mean one specific thing: *this piece of
content has been physically stuck onto the page for quick reference* —
the way someone pastes a real sticky note onto a real piece of paper to
flag something to check later. If a card isn't that kind of reminder/
reference content, it gets no tape and no pin at all. On most pages,
most cards will have neither.

**Tape** and **pin** decorations, when used, sit just above the card's
top edge (`top: -8px` to `-11px`, absolutely positioned), gold-toned,
and rotate a few degrees off-axis for a hand-placed feel — this
positioning detail is unchanged from before. What changed is *when*
they're used at all, not how they're drawn.

## Sticky note — reminder/"note to self" content only

Reserved specifically for content the user wrote as a reminder to
themselves. A "notes to self" field is the canonical example — Spendly's
profile page Notes card is exactly this kind of content, and is the
reference case for this treatment going forward. Visual treatment is
unchanged from the original system: **no torn edge** — clean rounded
rectangle (`border-radius: 10px`), pastel background (`--sticky` /
`--sticky-mint`), its own drop shadow, a small tape strip pinning it
down, `--font-hand` for its content. Never apply this treatment to
anything that isn't reminder/note content — a stat tile or a data table
is never a sticky note, no matter how small.

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
- Apply grain, crease, or the aged-paper filter to an individual card —
  that texture lives at the page level only now, not per component.
- Give a card a torn edge — retired system-wide by this revision.
- Add tape or a pin to a card that isn't genuinely reminder/reference
  content stuck onto the page for quick lookup — most cards get neither.
- Put ruled-notebook lines on anything that isn't a reference/notes card.
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
  content a real user should ever see. The same rule applies to any
  future reference image shown for style only (colors/spacing/typography/
  treatment) — never copy its placeholder text onto a real page. Real
  page content always comes from the spec or the page's own data.
