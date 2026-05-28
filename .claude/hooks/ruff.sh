#!/usr/bin/env bash
# PostToolUse hook: auto lint+format an edited Python file with ruff.
# Safe no-op when ruff is absent or the edited file is not .py. Always exits 0.

# Prefer the project venv's ruff; fall back to a global ruff. No-op if neither exists.
if [ -x "${CLAUDE_PROJECT_DIR:-.}/.venv/bin/ruff" ]; then
  RUFF="${CLAUDE_PROJECT_DIR:-.}/.venv/bin/ruff"
elif command -v ruff >/dev/null 2>&1; then
  RUFF="ruff"
else
  exit 0
fi

# The harness passes the tool call as JSON on stdin; pull out the edited file path.
file=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
[ -z "$file" ] && exit 0

case "$file" in
  *.py)
    "$RUFF" check --fix "$file" >/dev/null 2>&1
    "$RUFF" format "$file" >/dev/null 2>&1
    ;;
esac
exit 0
