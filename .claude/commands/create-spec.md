---
description: Sync with main, create a feature branch, and write a numbered spec document for a new feature
argument-hint: "[feature-name] [step-number]"
allowed-tools: Write, Task, AskUserQuestion, Bash(git:*)
---

<!--
  create-spec.md — Spendly, final version.

  Restructured to mirror the instructor's Video 8 file: one job per
  numbered step, in the order they actually happen, not a separate
  "setup" section bolted on top. Every step below also carries a "Why"
  line — this is the "explain each step clearly, don't trust Claude Code
  to be consistent on its own" principle, applied to the file itself, not
  just described about it.

  One deliberate difference from the instructor's file, called out here
  instead of silently copied: his Step 1 has Claude run `git status`
  live and check the result. This file instead pre-loads that same check
  as an injected `!` line below, before Claude even starts. The real
  benefit of that: the check can't be skipped or the wrong command
  typo'd, since it always runs. It does NOT mean a dirty tree
  auto-aborts the command — `git status --porcelain` exits 0 whether the
  tree is clean or dirty, so Step 1 below still depends on Claude
  correctly reading the output, same as a live "run this and check" step
  would. Same idea (and same caveat) for the branch and spec listings
  below.

  Correction made on review: an earlier draft ran `mkdir -p .claude/specs`
  inside the injected `!` line below, so a brand-new project wouldn't
  fail the listing. That's a filesystem write, not a read, so per this
  project's own rule (CLAUDE.md, "Custom slash commands") it can't live
  in a `!` block — those must stay strictly read-only, with no
  permission prompt, same reasoning that moved the `INSERT` out of
  `seed-user.md`/`seed-expense.md`. The listing below instead tolerates
  a missing directory (`|| true`) without creating anything; the
  directory gets created implicitly when the spec file is written in
  Step 9.
-->

Create a spec document for the feature `$0`. Approach this like a senior
software engineer scoping real work, not a template-filling exercise.
Follow the numbered steps below in order — each one has a Why line
explaining what breaks if it's skipped or left to judgment instead of
followed exactly as written.

## Pre-loaded, read-only context (see the note at the top of this file for why these are injected instead of run live)

Working tree status:
!`git status --porcelain`

Existing specs (tolerates a missing directory — doesn't create one):
!`ls .claude/specs/ 2>/dev/null || true`

Existing feature branches, local and remote:
!`git branch -a --list "feature/*"`

Latest from origin, remote-tracking refs only, no local changes:
!`git fetch origin`

## Step 1 — Confirm the working tree is clean

If the `git status --porcelain` output above is non-empty, tell the user
the working tree isn't clean and **stop here**.

**Why:** every step after this one changes something (a branch, a file).
Starting from a dirty tree means you can't tell your changes apart from
whatever was already uncommitted, and a mistake becomes unrecoverable
instead of a clean `git checkout --`.

## Step 2 — Parse the feature name and optional step number

Slugify `$0` into kebab-case (e.g. `user authentication` →
`user-authentication`). If `$1` was given, that's an explicit spec/step
number — zero-pad it to 2 digits and use it as-is later. If `$1` wasn't
given, you'll auto-compute the next number in Step 9 instead.

**Why two ways to number:** a fixed roadmap (Spendly's numbered steps)
needs a specific number chosen on purpose, not just "whatever's next" —
skipping ahead or filling in a gap should still land on the right number.
A feature that isn't part of a pre-planned sequence doesn't have that
constraint, so auto-increment is the simpler default for it. Neither
mode is more "correct" — they fit different situations.

## Step 3 — Check the roadmap

You already have `CLAUDE.md` loaded for this session. Check whatever
step/feature tracking it keeps (a table, a checklist, a "done" column).
If `$0` or the step number from `$1` is already marked complete there,
**stop and tell the user** instead of proceeding.

**Why:** this is the one check the docs don't hand you for free — it's
specific to how *this* project tracks progress, not a general Claude Code
mechanism. Skipping it is how you regenerate a spec for something that
was already built.

## Step 4 — Check for a duplicate spec

Look through the existing-specs listing above for any file whose name
already contains the slug from Step 2. If one exists, **stop and tell the
user** which file matches, and ask whether to proceed anyway (e.g. to
revise an existing spec) before continuing.

**Why:** the existing-specs listing above was originally read only to
pick the next number. Reading it without also checking for a name match
is how the same feature quietly ends up with two specs.

## Step 5 — Sync with main

Check whether local `main` is behind `origin/main`
(`git rev-list HEAD..origin/main --count`). If it's behind, run
`git pull origin main` yourself, via your Bash tool.

**Why this is a live step, not an injected one:** unlike the read-only
checks above, this can change local files (a merge). Anything that
mutates the repo happens as a deliberate action you take, never as an
automatic injected line.

## Step 6 — Create the feature branch

Check the existing-branches listing above for `feature/<slug>`. If it's
free, use it as-is. If it's already taken (e.g. an abandoned earlier
attempt), don't error out — find the highest existing `feature/<slug>-NN`
suffix and use the next number, zero-padded to 2 digits (e.g.
`feature/registration` taken → try `feature/registration-01`, then
`-02`, and so on). Run `git checkout -b <that name>` yourself, branching
off `main`.

**Why:** without this fallback, re-running the command on a feature
you'd already started (and abandoned, or are resuming) just errors out on
a name collision instead of picking up cleanly.

## Step 7 — Explore the codebase

Use the `Explore` subagent to survey anything relevant to `$0` — existing
routes, schema, similar patterns — before writing a line of the spec.

**Why a subagent instead of you reading files directly:** keeps this
exploration out of your main context window, so the spec-writing step
below isn't competing for space with every file the exploration touched.

## Step 8 — Interview the user

A feature name like "profile page" pulls attention toward its editable
half by default — form fields, validation, what gets submitted — because
that's the concrete, obvious part. Nothing forces a separate look at the
read-only half, so it silently drops out unless you ask for it on
purpose. Ask these as genuinely separate `AskUserQuestion` questions, not
one blended one:

1. **Mutation** — "What should the user be able to change or submit
   here?"
2. **Display** — "What should the user see here that they can't change —
   summaries, history, any other read-only content?"

Then, before moving on:

- **Check for an existing design reference.** If a mockup, prototype,
  Figma reference, or artifact for this feature already exists —
  including one shown in an earlier, unrelated-seeming conversation this
  session or a prior one — walk through it item by item with the user and
  ask which pieces are real functional requirements versus pure
  decoration. A reference shown once, in passing, elsewhere, must not
  silently fail to become a requirement here.
- **Ask the boundary question whenever a related-but-deferred feature
  exists.** If CLAUDE.md's roadmap or Future Tasks lists something related
  that's being built later (e.g. a Dashboard), ask explicitly: "Given
  [related feature] is being built separately later, is there any
  summary/at-a-glance version of that data that still belongs on *this*
  page in the meantime?" Get that boundary settled here, not negotiated
  reactively after the spec is already written.
- **Close with a catch-all**, right before Step 9: "Is there anything else
  this page should show or do that we haven't covered yet?"

Across all of this: don't invent requirements the user hasn't stated.

**Why:** a spec is only as good as its assumptions, and an assumption
doesn't have to be *wrong* to be a problem — it can just be *incomplete*.
A single blended "functional requirements" question reliably captures the
mutation half of a feature and just as reliably misses the display half,
because nothing about asking it makes you notice what it left out. The
mockup check and the boundary question close the two other ways that gap
showed up in practice: a visual reference from a different conversation
thread never turning into a written requirement, and a deferred feature's
boundary being decided implicitly instead of asked about.

## Step 9 — Write the spec

Decide the number: use `$1` (zero-padded) if it was given in Step 2;
otherwise, the highest existing `NN-` prefix in `.claude/specs/` + 1,
zero-padded to 2 digits.

Write `.claude/specs/NN-<slug>.md` (your own Write tool call — never a
`!` block) with exactly these 10 sections, in this order, each a plain
`##` heading, filled with real content grounded in Steps 3, 7 and 8 — no
placeholders:

1. **Problem Statement** — what the feature does, or the problem it solves.
2. **Functional Requirements** — what the feature must do.
3. **APIs** — input, output, and data shape.
4. **Files and Interfaces Involved** — the specific files that will change
   and what interfaces (functions, routes, data models) they expose/modify.
5. **Constraints** — anything the implementation must respect (tech stack,
   existing conventions, performance, etc.).
6. **Out of Scope** — what this feature explicitly will NOT do.
7. **Edge Cases and Error Handling** — failure modes and how they're handled.
8. **Acceptance Criteria** — checklist for when this is considered done.
9. **Manual Verification Guide** — the developer driving this project is a
   beginner and does not yet know how to verify acceptance criteria on
   their own. For *every* item in section 8, write explicit, beginner-safe,
   step-by-step instructions for checking it by hand: exact UI paths (e.g.
   "DevTools → Application tab → Storage → Cookies → pick the origin
   matching your URL bar exactly"), exact commands to run (`curl`, `pytest`,
   a `sqlite3` read-only query), and the exact expected output/result for
   each. Assume no prior familiarity with the tool being used — this
   section is a manual, not a hint.
10. **End-to-End Verification** — a concrete, runnable step that proves the
    feature works once implemented.

**Why these 10 and not fewer:** sections 1, 2, 3, 5, 7 and 8 (Problem
Statement, Functional Requirements, APIs, Constraints, Edge Cases and
Error Handling, Acceptance Criteria) were requested up front. Sections 4,
6 and 10 (Files and Interfaces Involved, Out of Scope, End-to-End
Verification) were added after checking the official Claude Code docs —
each closes a real gap the other 6 leave open (which files actually
change, what's deliberately excluded, and how anyone proves it worked).
Section 9 (Manual Verification Guide) was added later still, specifically
because the developer here can't yet verify acceptance criteria
unassisted — see CLAUDE.md's "Spec verification convention".

## Step 10 — Report back

Print a short summary in exactly this format, then stop — do not paste
the full spec into the chat unless the user explicitly asks for it:

```
Branch:    <branch name>
Spec file: .claude/specs/<NN>-<slug>.md
Title:     <feature title>
```

Then tell the user to review the spec file, then enter Plan Mode
(`Shift+Tab`) to begin implementation.

**Why print a fixed format instead of a free-form summary:** you'll run
this command dozens of times across a project. A fixed, scannable format
means you can tell at a glance what just happened without re-reading
prose each time.

## Convention — pairing a plan with the spec

Every numbered spec in `.claude/specs/` is expected to get a matching
numbered plan in `.claude/plans/NN-<slug>.md` once Plan Mode produces
one (see `.claude/plans/01-database-setup.md` for the shape: Context/
Scope, a section per file changed, a Verification section tied to the
spec's End-to-End Verification, and an Explicitly-out-of-scope
section). This command only writes the spec — it doesn't create the
plan file itself, since planning happens later in Plan Mode — but when
guiding the user afterward, mention that the plan produced by Plan
Mode should end up committed at `.claude/plans/NN-<slug>.md` using the
same number as the spec, not left only as a local Plan Mode scratch
file.

**Why:** the spec documents *what* and *why*; the plan documents *how*
it was actually broken into edits, and pairing the two numbers makes
both easy to find together later. Without this note it's easy to
finish planning and skip committing the plan, since Plan Mode's own
output file lives outside the repo by default.

## Convention — verifying the implementation

Once a spec is built, **the main agent never verifies its own
implementation.** Verification follows the SDD workflow in `CLAUDE.md`:

1. **Validate** — hand the spec's Manual Verification Guide to the
   developer to run by hand.
2. **`/test-feature <spec-name>`** — `spendly-test-writer` writes tests
   from this spec (never from the code), `spendly-test-runner` runs them.
   Write the Acceptance Criteria so each item is testable: exact field
   names, status codes, redirect targets and error messages. Anything
   missing comes back as a `SPEC GAP:` line.
3. **`/code-review-feature <spec-name>`** — `spendly-security-reviewer`
   and `spendly-quality-reviewer` review the diff in parallel.

Commit only when all three pass.
