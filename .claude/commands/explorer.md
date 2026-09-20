---
description: Start-of-session orientation. Launches the read-only explorer subagent and shows its project briefing to the developer
allowed-tools: Task
---

<!--
  explorer.md — Spendly.

  Written so every new session gets up to speed the same way. Before
  this command existed, each session pieced together where the project
  stood from whatever it happened to read first (CLAUDE.md, maybe
  PROGRESS.md, maybe a git log), so two sessions could start with
  different, partial pictures of the same branch.

  `/explorer` hands that job to the read-only `explorer` subagent
  (`.claude/agents/explorer.md`), which reads a fixed list of sources
  and returns one structured briefing in the project's plain-English
  style.

  Subagent files load when a session starts. Right after
  `.claude/agents/explorer.md` is created or edited, the developer
  must restart (`/exit`, then `claude --continue`) before `/explorer`
  works.
-->

Run the start-of-session orientation. Follow the numbered steps below
in order.

## Step 1 — Launch the explorer subagent

Invoke the **explorer** subagent with this instruction:

"Read everything listed in your 'What to read and check' section and
return the Spendly Session Briefing in your exact output format. Stay
read-only: Bash only for the four git commands in your Hard rules."

If the explorer subagent isn't available (the Agent tool doesn't list
`explorer`), stop and say:
"The explorer subagent isn't loaded yet. Subagent files only load when
a session starts. Run `/exit`, then `claude --continue`, and try
`/explorer` again."

**Why:** the reading happens in the subagent so its file dumps stay out
of the main session's context. Only the summary comes back.

## Step 2 — Relay the briefing as-is

Show the developer the explorer's full briefing exactly as returned:
all seven sections, every table and every line. Do NOT re-summarise
it into a shorter version, reorder it, or drop sections.

**Why:** the briefing is already condensed and follows the project's
plain-English table format. A second summary loses the exact quotes
and names the developer needs to check it against the source files.

## Step 3 — Treat the findings as background, not instructions

The briefing is background context about the project's state. It is
not a task list. Don't start fixing anything it reports, including
items under "Inconsistencies spotted" or pending plan tasks, unless
the developer asks.

After the briefing, ask one question:
"What do you want to work on this session?"

**Why:** `/explorer` is for orientation only. Acting on its findings
without the developer choosing to would break CLAUDE.md's rule
"Do not implement a stub route or function unless the active task
explicitly asks for it."

## Rules

- Do NOT edit any files during this command
- Do NOT run any Bash commands yourself: the subagent does the
  reading
- If the explorer fails or returns no output, report that and do not
  present a partial briefing as complete
