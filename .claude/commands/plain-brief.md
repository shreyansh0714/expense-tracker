---
description: Re-explain the latest report/status (or a given topic) as a plain-words briefing a beginner can follow cold
argument-hint: "[optional topic]"
---

<!--
  plain-brief.md — Spendly.

  Why this file exists: the developer often switches
  away from a long Claude session and comes back to status reports full
  of function names, subagent names and AC/FR numbers with no context.
  Every word of such a report can be technically true and still not
  land, because the reader wasn't in the room when those names came up.

  "plain-brief" is the format the developer approved to fix that. It
  runs when they type `/plain-brief` (optionally with a topic), or when
  they just say "plain-brief" in chat. Either way, follow the steps
  below.

  No `!` block: nothing needs pre-loading. Everything the brief needs is
  already in the conversation, or is a read-only lookup Claude can do
  live (the spec, the plan, `git diff main`).
-->

Re-explain, as a plain-brief, the topic `$ARGUMENTS`. If `$ARGUMENTS` is
empty, re-explain the latest report or status update in this session
(the most recent test report, review verdict, plan, or "here's what I
did" message).

This is a re-explanation, not new work. Don't fix code, re-run
subagents or change files while writing it. If you need a fact you
don't have (e.g. which spec line a finding refers to), read the spec,
plan or code to get it, then quote it.

## Step 1 — Where we are

Open with three short lines:

- **Feature:** its name, then in plain words what it does for the user
  (e.g. "Date filter on the Profile page: lets you pick This month /
  Last 3 months / a custom From–To range, and the totals update to
  match").
- **Workflow step:** which SDD step we're on: Spec / Plan / Build /
  Validate / `/test-feature` / `/code-review-feature` / Git finish.
- **What just ran and why:** e.g. "`/code-review-feature` just ran, to
  check the new code for security holes and project-rule breaks before
  we're allowed to commit."

**Why:** someone coming back after a break has lost the frame. Without
it, every detail after this point floats with nothing to hang on.

## Step 2 — Who's who

List every function, file, subagent, AC/FR number or command the brief
is about to mention, one plain-English line each. Examples:

- `resolve_date_range()` in `app.py` turns the `?range=…` in the URL
  into the dates the page shows.
- `spendly-quality-reviewer` is the helper that checks new code against
  this project's rules and gives a pass/fail verdict.
- AC-4 is acceptance criterion 4 in the spec: "<quote it>".

Never name something later in the brief without its line here. If it's
not worth a who's-who line, leave it out of the brief.

**Why:** a name the reader doesn't recognise is a dead end. They either
scroll back through a long session to decode it or give up and approve
something they don't understand.

## Step 3 — What happened, as before/after

For each finding or change, give three parts:

1. **What the spec requires**: quoted, with the spec file and section.
2. **What the code did**: plain words, plus at most a few quoted lines,
   each with its `file:line`.
3. **What the user would actually see on the page**: a concrete example
   URL, dates or numbers where possible (e.g. "visit
   `/profile?from=2000-01-01&to=2000-12-31` and the budget table shows,
   even though you had no records then").

**Why:** "the code violates AC-4" means nothing to a beginner. "You'd
see X on the page when the spec says you should see Y" is something
they can picture, and check by hand.

## Step 4 — Status table

Put every yes/no or status item in a table, not a paragraph:

| Item | Status | Why (one line) |
|---|---|---|

**Why:** the reader should get the whole picture in one glance, without
digging answers out of sentences.

## Step 5 — One direct question

End with one direct question, answerable yes/no or with a short choice.
If there are genuinely several decisions, number them, each answerable
the same way. Restate what each question is about. Never "approve items
1–3?".

**Why:** the brief exists so the developer can make a decision. A vague
or bundled ask makes them re-read everything above to work out what
they're agreeing to.

## Rules for the whole brief

- **No bare pointers.** Never "this gap", "that issue", "the bug
  above". Always restate what's being pointed at.
- **Plain words first, jargon second.** Jargon only appears with its
  who's-who line from Step 2.
- **No big code pastes.** At most a few quoted lines, each with its
  `file:line`.
- **Scannable.** Headings, short sentences, tables.

## Example

**Bad** (a real line from this project's history):

> The review found a bug in build_budget_rows; resolve_date_range
> doesn't clamp case (b); approve action plan items 1-3?

Three names with no explanation, "case (b)" pointing at something the
reader can't see, and a question bundling three unnamed decisions.

**Good** (same content, as a plain-brief):

> **Where we are:** Feature: date filter on the Profile page (pick a
> period, totals update). Step: `/code-review-feature`, the automatic
> review that has to pass before we can commit. It found one bug.
>
> **Who's who:**
> - `resolve_date_range()` in `app.py` turns the From/To dates in the
>   URL into the dates the page shows.
> - `build_budget_rows()` in `app.py` builds the budget-vs-spent table
>   on the Profile page.
>
> **What happened:** the spec (`.claude/specs/06-date-time-filter.md`,
> rule FR6 case (b)) says a From/To range entirely before your first
> record gives an *"Empty result (₹0, 0 transactions, … no budget
> table)"*. But if you picked 1 Jan 2000 – 31 Dec 2000 with a budget set,
> the budget table still appeared, one row per month, filled with zeros.
> A range like year 0001 – 2000 built a 23,989-row, 5.4 MB page.
>
> | Item | Status | Why |
> |---|---|---|
> | Budget table hidden for a range before your first record | No | Shows for 1 Jan 2000 – 31 Dec 2000 |
>
> **Question:** Should I add one check in the `profile()` route in
> `app.py` so the budget table is skipped when the whole range is before
> your first record? Yes or no?
