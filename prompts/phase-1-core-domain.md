# Phase 1 — Core domain (Document, render, writer)

## Context
Build the domain core that everything else feeds into. No handlers, no LLM, no network.
Read `.claude/rules/handler-contract.md` (the `Document`) and `.claude/rules/output-format.md`
(exact frontmatter + filename rules) before starting.

## Goal
A `Document` → Obsidian `.md` file path, byte-exact and slugified, fully tested.

## Build
1. `any2md/models.py`: the `Document` dataclass exactly per `handler-contract.md`.
2. `any2md/render.py`: `render(doc) -> str`. Produces YAML frontmatter (required keys:
   `title`, `source_url` if present, `source_type`, `extraction_date`, `upload_date` if
   present, `tags`) + body (`# title`, optional `> **Summary:**`, optional inline
   `[[wikilinks]]` line, then `body_markdown` under a section heading). Omit absent keys
   (never write `null`). Follow `output-format.md` precisely.
3. `any2md/writer.py`: `write(doc, output_dir) -> Path`. Slugify title → filename,
   append numeric suffix on collision, create dir if missing, write the rendered string.

## TDD
- `tests/test_render.py`: golden-file test — a fixed `Document` (with and without summary/
  tags/wikilinks) renders byte-exact to `tests/fixtures/golden_*.md`.
- `tests/test_writer.py`: slugify cases (punctuation, spaces, unicode), collision →
  `-2`/`-3`, writes into a tmp dir, returns correct path.

## Done when
- `pytest -q` green; `ruff check .` clean.
- A throwaway script building a `Document` and calling `write(doc, "/tmp/out")` produces a
  valid Obsidian `.md` you can eyeball.

## Stop
Show a sample rendered `.md` and the test output. Wait for manual review before Phase 2.
