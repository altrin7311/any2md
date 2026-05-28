# Rule: Testing (TDD)

Write the test first, watch it fail, then implement. No live network in tests.

## Per layer
- **Handlers** — record a fixture once (saved HTML/JSON/sample file under `tests/fixtures/`),
  then assert `extract()` returns the expected `Document` fields. Mock/replay HTTP; never
  hit the real site in CI.
- **Enricher** — inject a fake `LLMProvider` returning canned summary/tags/wikilinks.
  Test both `provider=none` (no enrichment) and an enriching provider.
- **render()** — golden-file test: fixed `Document` → byte-exact expected `.md`.
- **writer** — slugify + collision-suffix unit tests; write to a tmp dir.
- **End-to-end** — one test per source through the full pipeline with all external calls mocked.

## Layout
```
tests/
├── fixtures/         # recorded responses + sample input files + golden .md
├── test_<handler>.py
├── test_enricher.py
├── test_render.py
├── test_writer.py
└── test_e2e_<source>.py
```

## Run
`pytest -q` (full) • `pytest tests/test_render.py -q` (one) • `/checks` runs tests + ruff.

A phase is "done" only when its tests are green and the manual check in its prompt passes.
