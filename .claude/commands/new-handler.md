---
description: Scaffold a new Any2MD source handler with a fixture test (TDD)
argument-hint: <source name, e.g. twitter>
---

Add a new source handler named `$ARGUMENTS` to Any2MD, TDD-first.

Delegate to the `handler-builder` subagent (it works in isolation and reports back compressed):
- Target source: `$ARGUMENTS`
- It must follow `.claude/rules/handler-contract.md`, `testing.md`, `output-format.md`.

After the subagent reports: register the handler in `registry.py` if not already done
(specialized URL handlers before the `web` fallback), run `/checks`, and summarize what changed.

If `$ARGUMENTS` is empty, ask which source to add.
