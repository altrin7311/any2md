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
├── test_<handler>.py     # youtube/reddit/github + test_new_handlers.py (hn/arxiv/wiki/so/x)
├── test_registry.py      # URL routing → correct handler; web is fallback
├── test_enricher.py
├── test_render.py
├── test_writer.py
├── test_queue.py · test_repl.py · test_server.py   # queue / REPL / serve
├── test_theme.py · test_eta.py · test_onboarding.py  # CLI polish, ETA, first-run
└── test_e2e_<source>.py · test_e2e_all.py
```
- Mock each handler's module-level `_fetch_*` helper (e.g. `reddit._fetch_json`,
  `reddit._fetch_rss`) to replay a fixture — never hit the network.
- Isolate global state with env: `ANY2MD_CONFIG` (config) and `ANY2MD_STATS` (ETA) → tmp paths,
  so tests never read or write the real `~/.any2md`.
- `serve` tests use `with TestClient(app) as client:` (the `with` keeps the queue's event
  loop alive across requests).

## Run
`pytest -q` (full) • `pytest tests/test_render.py -q` (one) • `/checks` runs tests + ruff.

A phase is "done" only when its tests are green and the manual check in its prompt passes.
