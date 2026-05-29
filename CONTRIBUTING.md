# Contributing to Any2MD

Thanks for helping out! Any2MD is a free, fully offline CLI — contributions must keep it that way.

## Ground rules

- **100% free / open-source.** No external APIs, no API keys, no paid hosting tier — ever.
- **Summarization is best-effort.** A missing binary, an unreachable Ollama, or an empty page
  must never crash a conversion — degrade with a terminal warning instead.
- **TDD.** Write the test first, watch it fail, then implement. No live network in tests — mock the
  module-level `_fetch_*` helpers and replay a saved fixture.

## Dev setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you push

```bash
pytest -q          # full suite, must stay green
ruff check .       # lint, must be clean
```

CI runs both on every push and PR (Python 3.11 + 3.12).

## Adding a new source

A source is one `Handler` (`matches` + `extract` → `Document`). See `.claude/rules/handler-contract.md`
for the contract and `.claude/skills/add-source-handler` for the TDD recipe: record one fixture,
assert the extracted `Document` fields, register the handler (URL handlers before the `web`
catch-all). Extraction only — no summarizing or file writing inside a handler.

## Project layout

`any2md/registry.py` (routing) · `handlers/*` (sources) · `enrich/*` (summarizers) ·
`render.py` · `writer.py` · `url.py` · `pipeline.py` · `queue.py` · `repl.py` · `server.py` ·
`theme.py` · `eta.py` · `onboarding.py` · `config.py`. Tests mirror these under `tests/`.
