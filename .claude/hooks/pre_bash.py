"""PreToolUse hook for Bash: blocks commands that break Spendly safeguards.

Exit code 2 = block the command; the stderr message is shown to Claude.
"""
import json
import re
import subprocess
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
cwd = data.get("cwd") or "."


def block(msg):
    print(f"BLOCKED: {msg}", file=sys.stderr)
    sys.exit(2)


# ------------------------------------------------------------------ #
# 1. Protect database.db                                              #
# ------------------------------------------------------------------ #
if re.search(r"\bdatabase\.db\b", cmd):
    # rm/unlink/truncate/mv only count at the start of a command, so
    # `echo "rm database.db"` or `git log` mentioning it stays allowed.
    if re.search(r"(^|[;&|(]\s*)(sudo\s+)?(rm|unlink|truncate|mv)\s", cmd, re.M):
        block("deleting/moving database.db — it holds your real data.")
    if re.search(r">\s*database\.db\b", cmd):
        block("overwriting database.db with a shell redirect.")
    if re.search(r"\bDROP\s+TABLE\b", cmd, re.I):
        block("DROP TABLE on database.db.")
    if re.search(r"\bDELETE\s+FROM\s+\w+\s*(;|'|\"|$)", cmd, re.I | re.M):
        block("DELETE without a WHERE clause on database.db (wipes the table).")

# ------------------------------------------------------------------ #
# 3. No commits or pushes on main                                     #
# ------------------------------------------------------------------ #
if re.search(r"\bgit\s+(commit|push)\b", cmd):
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=cwd, capture_output=True, text=True
    ).stdout.strip()
    if branch == "main":
        block("you're on main. SDD step 1: git checkout -b feature/<name> first.")
    if re.search(r"\bgit\s+push\b.*\bmain\b", cmd):
        block("pushing to main — push the feature branch and merge via a PR.")
