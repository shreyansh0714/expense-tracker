---
description: Read a spec, explore the codebase, ask what's still open, and write an implementation plan split into a Design Plan and a live Tasks checklist
argument-hint: "[spec-file-path]"
allowed-tools: Read, Task, AskUserQuestion, Write, Bash(git status:*)
---

<!--
  implement-plan.md — Spendly.

  Written after `.claude/specs/04-profile-page.md` was planned by hand in
  Plan Mode, with the developer explicitly asking for two things a spec
  alone doesn't give you: (1) the plan's design reasoning kept visibly
  separate from its task list, so it's reviewable at a glance instead of
  one undifferentiated wall of prose, and (2) a checklist that's actually
  kept current *during* implementation, not just written once and left
  stale — the developer's own observation was that past plans had
  checklists that were never updated while the work happened, which
  defeats the reason to write one down in the first place.

  This command is meant to be run from inside Plan Mode (the same way the
  developer typed free-form planning instructions to `/plan` before this
  command existed) — `argument-hint` takes the spec file to plan against.
  It doesn't toggle Plan Mode itself; Plan Mode's own file-write
  restriction already gates Step 5's Write call to the scratch plan file
  until the user approves it, same as it would for hand-typed instructions.
-->

Create an implementation plan for the spec at `$0`. Follow the numbered
steps below in order.

## Step 1 — Read the spec

Read `$0` in full.

**Why:** the spec is the source of truth for *what* to build — Functional
Requirements, APIs, Files and Interfaces Involved, Constraints, Out of
Scope, Edge Cases, and Acceptance Criteria all come from here. Nothing in
the steps below should contradict it.

## Step 2 — Read CLAUDE.md's plan conventions

You already have `CLAUDE.md` loaded for this session. Re-read its "Plan
checklists" section (and anything else relevant — coding conventions,
"Critical rules") before writing anything.

**Why:** the output of this command has to match how this project already
does things, not introduce a competing convention.

## Step 3 — Explore the codebase

Use the `Explore` subagent to check whether the files named in the spec's
"Files and Interfaces Involved" section still match reality, and to
surface existing patterns worth reusing for the new work.

**Why a subagent instead of reading files directly:** same reasoning as
`create-spec.md` Step 7 — it keeps the exploration out of the main context
window, so writing the plan afterward isn't competing for space with every
file the exploration touched.

## Step 4 — Ask what's still open

Use `AskUserQuestion` for anything the spec leaves genuinely undecided —
UI/UX micro-decisions the spec doesn't pin down, implementation sequencing,
whether to add automated tests, anything with more than one reasonable
approach. Don't invent an answer the user hasn't given.

**Why:** a spec documents *what* to build, not every *how*. A spec that
says "add a toast" without saying where it sits on screen or how long it
stays up still leaves real decisions open — guessing at them here is how
an implementation quietly diverges from what the user actually pictured.

## Step 5 — Write the plan

Decide the number: reuse the spec's own `NN-<slug>` filename base (e.g.
`.claude/specs/04-profile-page.md` → `.claude/plans/04-profile-page.md`),
per `create-spec.md`'s existing "pairing a plan with the spec" convention.

Write `.claude/plans/NN-<slug>.md` (your own Write tool call) with exactly
two top-level sections, in this order:

1. **Design Plan** — the architecture/approach for each non-obvious part
   of the implementation, and *why* — what's reused from existing code
   versus genuinely new, and the reasoning behind any judgment call (e.g.
   "no decorator yet, only one call site needs this guard so far").
2. **Tasks** — a literal `- [ ]` checklist, one item per independently
   completable unit of work, ordered so each item's dependencies come
   before it (e.g. a new DB function before the route that calls it).

Add a short "Explicitly out of scope" section mirroring the spec's Out of
Scope, and a "Verification" section pointing at the spec's own Acceptance
Criteria / Manual Verification Guide / End-to-End Verification rather than
restating them.

**Why exactly these two sections, not one:** a plan that blends reasoning
and task tracking makes both harder to use — reviewing the *why* means
wading through checklist items, and checking progress means wading through
prose. Splitting them means each does its one job.

## Step 6 — Keep the checklist live during implementation

This is a standing rule for whoever implements this plan, in this session
or a later one — state it plainly in the plan file itself, not just here:
**immediately after finishing each task, re-open the plan file and check
its box.** Don't batch updates to the end of a session, and don't rely on
memory to know what's done.

**Why:** the entire reason to write a checklist down instead of just
holding the plan in your head is that it survives things your head
doesn't — a mid-implementation context compaction, a resumed session hours
or days later, a different person picking up the file. A checklist that's
only accurate once everything is finished provides none of that; it has to
be accurate *while the work is still in progress* to be worth anything.

## Step 7 — Report back

Print a short summary in exactly this format, then stop:

```
Plan file: .claude/plans/<NN>-<slug>.md
Tasks:     <N> items
```

Then tell the user to review the Design Plan and Tasks checklist before
implementation starts (or continues, if this plan is being reviewed after
some work is already done).

**Why a fixed format:** same reasoning as `create-spec.md` Step 10 — a
scannable, consistent summary beats re-reading prose every time this
command runs.
