# Phase 3 — LLM enrichment (summary, tags, wikilinks)

## Context
Add the pluggable LLM layer that summarizes every input. Read `.claude/rules/tech-stack.md`
(provider env vars), `output-format.md` (where summary/tags/wikilinks land). Depends on
Phase 2 pipeline. **Hard constraint: never hard-fail on a missing key — `none` still works.**

## Goal
Converted files gain a summary, `#tags`, and `[[wikilinks]]` when an LLM is configured;
identical extraction-only output when `provider=none` or the key is absent.

## Build
1. `any2md/enrich/base.py`: `LLMProvider` ABC — `complete(prompt, system="") -> str`,
   optional `describe_image(path) -> str | None`.
2. `any2md/enrich/groq.py` (default) and `any2md/enrich/gemini.py`. Lazy-import the SDK so a
   missing dep/key for one provider never breaks others. Read keys from env only.
   (Cloudflare + Ollama may be stubbed with a clear `NotImplementedError` for a later pass.)
3. `any2md/enrich/enricher.py`: `enrich(doc, provider)` — fills `doc.summary`, `doc.tags`,
   `doc.wikilinks` in one or few calls. Long `body_markdown` chunked (or sent whole on
   large-context providers). If `provider=none` or no key → return doc unchanged.
   If a vision-capable provider is set and `source_type=image` → add a description.
4. Replace the Phase 2 stub: pipeline now calls the real `enricher.enrich`.
5. Provider selection from config/env in `config.py` + a `provider_from_config()` helper.

## TDD
- `tests/test_enricher.py`: a `FakeProvider` returns canned summary/tags/wikilinks →
  assert they land on the `Document` and in rendered output. Assert `provider=none`
  leaves doc unchanged. Assert missing key path degrades gracefully (no exception).
- No real API calls in tests — providers are injected/mocked.

## Done when
- `pytest -q` green; `ruff check .` clean.
- With `GROQ_API_KEY` set + `provider=groq`: `any2md convert <file>` output has a real
  summary + tags + wikilinks.
- With `provider=none` (or key unset): same file converts, no summary section, no crash.

## Stop
Show one enriched `.md` and one extraction-only `.md`. Wait for manual testing before Phase 4.
