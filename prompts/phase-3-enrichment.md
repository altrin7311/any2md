# Phase 3 — Enrichment (summary, tags, wikilinks) — no APIs, no keys

## Context
Add the pluggable summarizer layer that summarizes every input. Read
`.claude/rules/tech-stack.md` (summarizers) and `output-format.md` (where summary/tags/
wikilinks land). Depends on Phase 2 pipeline.
**Hard constraint: no external APIs, no API keys. Enrichment is best-effort — `none` (or any
summarizer error / unreachable Ollama) still produces full extraction-only output.**

## Goal
Converted files gain a summary, `#tags`, and `[[wikilinks]]` with **zero setup** (extractive
default); identical extraction-only output when `provider=none`.

## Build
1. `any2md/enrich/base.py`: `Summarizer` ABC — `summarize(title, body) -> dict`
   returning `{"summary": str, "tags": list[str], "wikilinks": list[str]}`.
2. `any2md/enrich/extractive.py` (**default**): pure-Python, no model/network/deps.
   Frequency/TextRank-style — score sentences by content-word frequency (top few →
   summary), frequent content words → tags, capitalized phrases → wikilinks. Safe on empty.
3. `any2md/enrich/ollama.py` (optional): POST a JSON-format prompt to a local Ollama server
   (`OLLAMA_URL` default `http://localhost:11434`, `OLLAMA_MODEL` default `llama3.2`) via
   lazy `httpx`; parse `{summary, tags, wikilinks}`. No key. Unreachable → raises (caught).
4. `any2md/enrich/providers.py`: `get_summarizer(name)` → `none`→None,
   `extractive`→ExtractiveSummarizer, `ollama`→OllamaSummarizer, else ValueError.
5. `any2md/enrich/enricher.py`: `enrich(doc, summarizer)` — fills `doc.summary/tags/wikilinks`;
   `None` or any exception leaves doc unchanged (best-effort).
6. Pipeline calls `enrich(doc, get_summarizer(provider))`. Default `provider=extractive`.

## TDD
- `tests/test_enricher.py`: a `FakeSummarizer` returns canned values → assert they land on the
  `Document` and in rendered output. `None` leaves doc unchanged. A raising summarizer is
  swallowed (no exception). `ExtractiveSummarizer` produces non-empty output on prose and is
  safe on empty. `get_summarizer` returns the right types and rejects removed/unknown names.
- No network in tests (don't call a real Ollama server).

## Done when
- `pytest -q` green; `ruff check .` clean.
- Default (`provider=extractive`): `any2md convert <file>` output has summary + tags +
  wikilinks, with no setup and no network.
- `provider=none`: same file converts, no summary section, no crash.

## Stop
Show one enriched `.md` (extractive) and one extraction-only `.md`. Wait before Phase 4.
