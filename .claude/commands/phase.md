---
description: Load and start an Any2MD implementation phase prompt
argument-hint: <phase number 0-6>
---

Read `prompts/phase-$ARGUMENTS-*.md` (the phase whose filename starts with `phase-$ARGUMENTS-`).

Then execute that phase exactly as written:
- Follow its TDD instructions (test first).
- Honor the hard constraints in `CLAUDE.md` and `.claude/rules/`.
- Build only what the phase scopes — nothing from later phases.
- When done, run the phase's "Done when" checks and report results.
- STOP at the phase boundary so I can test manually before moving on.

If `$ARGUMENTS` is empty, list the available phase prompts in `prompts/` and ask which to start.
