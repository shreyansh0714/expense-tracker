---
name: spendly-ui-polish
description: >
  Applies Spendly's paper-and-receipt visual design system — torn edges,
  grain texture, tape/pins, ruled-notebook cards, printed receipt strips,
  italic serif titles, pastel sticky notes — to a page in this Flask
  expense-tracker project whose structure, route, and data are already
  built. Use this whenever a Spendly template needs visual polish: a form,
  a stat/dashboard panel, a list or receipt-style view, a "notes" or
  reference card, any freshly-implemented page. Also use it whenever the
  user says "beautify", "polish", "make this look good/nicer", "apply the
  paper theme", or similar, for any page in this project — even without
  the word "skill" attached. Do NOT use it to write specs, plan an
  implementation, add routes/fields/database changes, or touch any
  backend logic in app.py or database/db.py — this skill only edits
  static/css, template markup, and small static/js interactions.
---

# Spendly UI Polish

Spendly is being built one Step at a time, and the same "make this page
look good" prompt kept getting re-typed by hand after every new page. This
skill exists so that prompt never has to be typed again — it encodes a
locked, specific visual language instead of inventing a new look each time,
so every page in the app reads as one coherent product.

## Why a locked design system instead of "just make it nice"

A vague "make it nice" produces a different aesthetic every time it's
asked, and Spendly would end up looking like five different apps stitched
together. This skill instead applies one specific system — the paper-and-
receipt look, locked from a prototype the developer reviewed and approved
(https://claude.ai/artifact/MJjs9Ed2iJcumWmXRyLDdw) — the same way a real
design system would be handed to any engineer touching the UI. Read
`references/design-system.md` for the full token values, CSS recipes, and
the component→treatment table before touching any file — it's the source
of truth, not a suggestion to riff on.

## Scope boundary — read this before editing anything

This skill polishes what already exists. It never invents what the page
contains.

- **May edit**: `static/css/style.css` (or a new page-specific CSS file),
  template HTML in `templates/*.html` (classes and purely decorative
  markup only), `static/js/main.js` (small visual interactions only —
  hover/toggle/settle animations, nothing that computes or fetches data).
- **Never edits**: `app.py`, `database/db.py`, any route signature, any DB
  schema or query, session/auth logic. If the page seems to be missing a
  field or behavior, that's a spec gap, not something this skill should
  invent — say so and stop rather than adding it.
- **Never invents new content.** If a spec or plan is available for the
  page being polished, read it only to learn *what's on the page* (a form?
  a list? a stat panel?) so the right treatment from the table applies —
  never as a source of colors, fonts, or layout rules. Those come only
  from `references/design-system.md`.
- **Reuse existing tokens.** `style.css` already defines `--ink`,
  `--paper`, `--accent` (forest green), `--accent-2` (gold), `--danger`,
  `--radius-*`, and the `DM Serif Display` / `DM Sans` pairing. Extend this
  set (see the reference file for the additions this system needs) —
  never redefine `--accent`, `--accent-2`, or `--danger` to a different
  value, and never introduce a second, competing color system.
- **No new dependencies.** Everything is vanilla CSS/HTML/JS, matching the
  rest of this project.

## Workflow

1. **Read the target template** (and its route in `app.py`, read-only) to
   see what's actually on the page — the content, not just the file name.
2. **Classify each section** against the component table in
   `references/design-system.md`: is it a content/stat panel, a printed/
   receipt-style list, a form, a reference/notes card, or a sticky-note/
   reminder? A single page can mix several — a profile page, for example,
   is a form panel plus maybe a notes card.
3. **Apply the matching treatment** from the reference file: the right
   torn-edge/rounded-corner choice, the right accent decoration (tape vs.
   pin vs. none), the right typeface for that content type, the grain/
   crease texture. Add any missing CSS custom properties to `:root` in
   `style.css` rather than hardcoding a new color inline.
4. **Leave structure and logic untouched.** Class names can change, markup
   can gain purely decorative wrapper elements, but form fields, routes,
   and data flow stay exactly as they were.
5. **Sanity-check in a browser** if the dev server is available (`python
   app.py`, port 5001) — the point of this system is that it should look
   like it belongs next to every other page in the app, not like a one-off.

## Reference

- `references/design-system.md` — full color/type tokens, the grain and
  crease CSS recipes, the torn-edge clip-path, and the component→treatment
  table. Load this before making any visual decision.
