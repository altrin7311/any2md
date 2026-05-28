# Phase 2 — Files handler + pipeline end-to-end

## Context
Wire the first real handler and the orchestrating pipeline. Still no LLM (`provider=none`).
Read `.claude/rules/handler-contract.md`, `testing.md`. Depends on Phase 1 (`Document`,
`render`, `writer`).

## Goal
`any2md convert <local file>` produces a correct `.md` in the output folder, for the
markitdown-supported types (pdf/docx/pptx/xlsx/csv/image/html/epub).

## Build
1. `any2md/handlers/base.py`: the `Handler` ABC (`matches`, `extract`).
2. `any2md/handlers/files.py`: wraps `markitdown`. `matches()` by file extension.
   `extract()` → `Document` (title from filename or doc title, `source_type` from extension,
   `source_url=None`, `upload_date=None`, `extraction_date=now`, `body_markdown` from
   markitdown). Image OCR text comes through markitdown; vision description is deferred to
   Phase 3.
3. `any2md/registry.py`: register handlers, `detect(target) -> Handler`. Files handler is
   the only one for now; structure it so URL handlers slot in later with `web` last.
4. `any2md/pipeline.py`: `convert(target, output_dir, provider) -> Path` running
   `detect → extract → enrich(no-op if none) → render → write`. Add a stub `enricher.enrich`
   that is a pass-through when `provider=none` (real enricher in Phase 3).
5. Wire `cli.py convert` to call `pipeline.convert`.

## TDD
- `tests/fixtures/`: tiny sample files (e.g. a small `.docx`, a `.csv`, a `.png` with text).
- `tests/test_files_handler.py`: `extract()` returns expected `Document` fields per fixture.
- `tests/test_e2e_files.py`: `convert(fixture, tmp_out, provider="none")` writes a `.md`
  with correct frontmatter and non-empty body.

## Done when
- `pytest -q` green; `ruff check .` clean.
- `any2md convert ./tests/fixtures/<sample>.docx -o /tmp/out` writes a real `.md`.

## Stop
Show the produced `.md` for a couple of file types. Wait for manual testing before Phase 3.
