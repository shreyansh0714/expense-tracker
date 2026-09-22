"""PostToolUse hook for Edit|Write: checks Python files right after Claude edits them.

Exit code 2 = the edit already happened, but the stderr message is fed back
to Claude so it fixes the problem straight away.
"""
import json
import py_compile
import re
import sys

data = json.load(sys.stdin)
tool_input = data.get("tool_input", {})
path = tool_input.get("file_path", "")
if not path.endswith(".py"):
    sys.exit(0)

problems = []

# ------------------------------------------------------------------ #
# 2. Python syntax check (stdlib, no black/ruff needed)               #
# ------------------------------------------------------------------ #
try:
    py_compile.compile(path, doraise=True)
except py_compile.PyCompileError as e:
    problems.append(f"Syntax error: {e.msg}")

# ------------------------------------------------------------------ #
# 4. No f-string / concatenated SQL in app.py or database/            #
# ------------------------------------------------------------------ #
# Only the newly written text is checked, so existing reviewed lines
# (e.g. the hardcoded ALTER TABLE loop in db.py) don't re-trigger.
if path.endswith("app.py") or "/database/" in path:
    new_text = tool_input.get("new_string") or tool_input.get("content") or ""
    unsafe = re.compile(
        r"\.execute(many|script)?\(\s*("
        r"f[\"']"                          # execute(f"...")
        r"|[\"'][^\"']*[\"']\s*[+%]"       # execute("..." + x) / ("..." % x)
        r"|[\"'][^\"']*[\"']\.format\("    # execute("...".format(x))
        r")"
    )
    for line in new_text.splitlines():
        if unsafe.search(line):
            problems.append(
                f"SQL built from a string: `{line.strip()}` — use ? placeholders "
                "(CLAUDE.md: always use parameterized queries)."
            )

if problems:
    print(f"{path}:\n- " + "\n- ".join(problems), file=sys.stderr)
    sys.exit(2)
