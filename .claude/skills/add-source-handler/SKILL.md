---
name: add-source-handler
description: Use when adding a new content source to Any2MD (e.g. Twitter, Hacker News, arXiv, a new file type) - the TDD recipe for writing one Handler that extracts a Document, registering it, and testing it against a saved fixture with no live network.
---

# Adding an Any2MD source handler

A "source" = anything Any2MD converts to Markdown. Each is one `Handler` that turns an
input (URL or file) into a `Document`. Follow this recipe exactly.

## Before you start — read the contracts
- `.claude/rules/handler-contract.md` — `Handler` ABC + `Document` fields you must fill.
- `.claude/rules/output-format.md` — which `metadata` keys are useful to the knowledge graph.
- `.claude/rules/testing.md` — fixtures, no live network.
- An existing sibling in `any2md/handlers/` for style.

## Recipe (TDD)
1. **Fixture.** Save one small real sample under `tests/fixtures/` (recorded HTML/JSON, or a
   sample file). This is what the test replays — tests never hit the network.
2. **Failing test.** Write `tests/test_<source>.py`: load the fixture, call `extract()`,
   assert the `Document` fields (title, source_type, dates, body_markdown, key metadata).
   Run it — confirm it FAILS for the right reason.
3. **Implement.** Create `any2md/handlers/<source>.py`:
   - `matches(target)` — cheap, side-effect-free (URL regex or file extension).
   - `extract(target)` — fetch/parse the fixture-shaped input, return a `Document`.
     No LLM calls, no file writing — extraction only.
4. **Register.** Add the handler to `registry.py` in priority order. Specialized URL
   handlers go BEFORE the `web` catch-all; `web` is always last.
5. **Green + clean.** `pytest tests/test_<source>.py -q` until green, then `ruff check --fix`
   and `ruff format`.
6. **E2E.** Add one `tests/test_e2e_<source>.py` running the full pipeline (external calls
   mocked) to confirm a `.md` is rendered and written.

## Guardrails
- One handler per task. Don't touch the enricher, renderer, or other handlers.
- If the source needs auth or a paid API, stop — Any2MD is free/OSS only. Find a public route.
- Put graph-useful facts in `metadata`; the renderer lifts selected keys into frontmatter.

## Delegating
For isolated, token-cheap work, dispatch the `handler-builder` subagent (`.claude/agents/`)
which follows this same recipe and reports back compressed.
