#!/usr/bin/env bash
# PostToolUse hook: auto lint+format an edited Python file with ruff.
# Safe no-op when ruff is absent or the edited file is not .py. Always exits 0.

command -v ruff >/dev/null 2>&1 || exit 0

# The harness passes the tool call as JSON on stdin; pull out the edited file path.
file=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
[ -z "$file" ] && exit 0

case "$file" in
  *.py)
    ruff check --fix "$file" >/dev/null 2>&1
    ruff format "$file" >/dev/null 2>&1
    ;;
esac
exit 0
