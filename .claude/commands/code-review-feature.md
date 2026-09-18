---
description: Runs parallel security and quality code 
  review for a specific Spendly feature. Pass the spec 
  name as argument e.g. /code-review-feature 03-login-and-logout
allowed-tools: Bash(git diff main), Bash(git ls-files --others --exclude-standard)
---

Run the full code review pipeline for the feature 
specified in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /code-review-feature 
<spec-name> e.g. /code-review-feature 03-login-and-logout"

If `.claude/specs/$ARGUMENTS.md` does not exist, stop 
immediately and say:
"Spec file not found at .claude/specs/$ARGUMENTS.md. 
Please check the spec name and try again."

## Pre-flight Check

Before invoking any subagents, collect every change on 
this branch:
- Run `git diff main` — all edits to tracked files 
  compared with `main`, whether committed, staged or not
- Run `git ls-files --others --exclude-standard` — 
  brand-new files that `git diff` never shows

If both are empty, stop immediately and say:
"No changes detected. Implement the feature before 
running code review."

---

## Step 1: Parallel Review

Invoke both subagents simultaneously with the same 
context:

**spendly-security-reviewer** receives:
- The `git diff main` output and the list of new files 
  (it must `Read` each new file in full)
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py`, `database/` 
  directory, `templates/` directory and `static/js/`
- Instruction: Review only the changed code for 
  security vulnerabilities. Do not comment on quality 
  or style.

**spendly-quality-reviewer** receives:
- The `git diff main` output and the list of new files 
  (it must `Read` each new file in full)
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py`, `database/` 
  directory, and `templates/` directory
- Instruction: Review only the changed code for quality, 
  Flask best practices, and maintainability. Do not 
  comment on security concerns.

Both subagents must run in parallel. Do not wait for 
one to finish before starting the other.

---

## Step 2: Unified Report

Once both subagents have completed, combine their 
findings into a single unified report. De-duplicate 
any overlapping findings — if both agents flagged the 
same line for different reasons, merge them into one 
finding with both perspectives noted.

Structure the combined report as:
Code Review Report — $ARGUMENTS
Security Findings
[spendly-security-reviewer output]
Quality Findings
[spendly-quality-reviewer output]
Combined Action Plan
Ordered checklist of everything that needs to be fixed,
prioritized by severity:

[Critical/High security findings first]
[Medium/Low security findings second]
[Quality items from a CHANGES REQUESTED verdict third]
[Quality items from an APPROVED WITH SUGGESTIONS verdict last]

The security reviewer's "FYI, not a finding" section is 
shown in the report but never goes in the action plan.

Overall Verdict
- CHANGES REQUESTED — must fix before committing, see 
  action plan above. Used when the security reviewer 
  reported ANY finding (any severity), or the quality 
  reviewer's verdict is CHANGES REQUESTED.
- Otherwise, use the quality reviewer's verdict:
  - APPROVED — ready to commit
  - APPROVED WITH SUGGESTIONS — can commit, address 
    suggestions in future steps
---

## Step 3: Ask for Approval

After presenting the unified report, ask:

"Do you want me to implement the action plan now?"

Wait for explicit user confirmation before making 
any changes. Do not touch any files until the user 
approves.

---

## Rules
- Do NOT edit any files before user approval
- Do NOT start one reviewer before the other — 
  both must run in parallel
- Do NOT skip the pre-flight diff check
- If either subagent fails or returns no output, 
  report it and do not present a partial review 
  as complete
