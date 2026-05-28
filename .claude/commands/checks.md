---
description: Run the Any2MD test + lint suite and report results
---

Run, in order, and report concise results (pass/fail counts, any failures verbatim):

1. `ruff check .` — lint
2. `ruff format --check .` — format check
3. `pytest -q` — full test suite

If anything fails, summarize the failures and stop (do not auto-fix unless I ask).
If all pass, say so plainly with the test count.
