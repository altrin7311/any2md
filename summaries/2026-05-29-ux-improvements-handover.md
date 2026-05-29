# Handover — Any2MD UX improvements

> Use this to start a fresh chat and implement the 7 UX edits below. Self-contained: read the
> Orientation, then work the edits in priority order. TDD per edit (test first, watch fail, implement).

---

## 0. Project in one paragraph

Any2MD is a free, open-source CLI that turns local files + web links into Obsidian-flavored
Markdown (one slugified `.md` per source, YAML frontmatter, every input summarized). Pipeline:
`registry.detect(target) → handler.extract() → enricher.enrich() → render() → writer.write()`.
**Hard constraints (never violate):** 100% free/OSS, no external APIs, no API keys ever;
summarization is best-effort (never hard-fail over enrichment); TDD per handler with no live
network in tests. Read `CLAUDE.md` + `.claude/rules/*` (handler-contract, output-format,
tech-stack, testing) before touching code.

## 1. Current verified state (as of 2026-05-29)

- **152 tests pass, `ruff check .` clean.** Run with `source .venv/bin/activate && pytest -q && ruff check .`.
- **Logo done** (`any2md/theme.py` `banner()`): "ANY" rainbow, "2" = right-pointing arrowhead,
  "MD" cyan. Don't re-touch unless asked.
- **Summarizer rewritten** (`any2md/enrich/extractive.py`): TextRank + prose-cleaning + MMR +
  mid-caps wikilink filter. Quality tests in `tests/test_extractive_quality.py`. Done.
- These edits below are **NOT started** — this handover is the work to do.

## 2. User working agreements (carry these in)

- User commits/pushes themselves — **do not commit or prompt to commit.**
- Show terminal commands the user should run wrapped as `||command||`.
- Ask when ambiguity arises; surface tradeoffs before coding.
- Surgical changes only — touch only what each edit needs.

---

## 3. The edits (priority order)

### 🔴 #1 — Detect missing system binaries (tesseract / ffmpeg) instead of cryptic crash

**Problem:** `pipx install any2md` cannot install `tesseract` (image OCR via markitdown) or
`ffmpeg` (youtube Whisper fallback). User drags a screenshot → raw markitdown traceback, no hint.
No `shutil.which` check exists anywhere.

**Fix:**
- In `any2md/handlers/files.py` `FilesHandler.extract`: for `source_type == "image"`, if
  `shutil.which("tesseract")` is None, still return a Document (file converted, body may be empty)
  but stamp `metadata["ocr_warning"]` (or surface via a clear message) telling the user:
  `install tesseract for OCR: brew install tesseract`. Never let markitdown traceback escape —
  wrap `self._md.convert` so a failed OCR degrades to empty body + warning, not a crash.
- youtube Whisper fallback (`any2md/handlers/youtube.py`): captions path needs no ffmpeg; only the
  Whisper fallback does. If that path is reached and `shutil.which("ffmpeg")` is None, skip Whisper
  and emit a clear "no captions; install ffmpeg for audio transcription" message rather than crash.

**TDD:** test in `tests/test_files.py` (or `test_new_handlers.py`): monkeypatch
`shutil.which` → None, mock `MarkItDown.convert` to raise, assert `extract()` returns a Document
with the warning and does NOT raise. No live network/binaries.

**Constraint tie-in:** best-effort — extraction must never hard-fail.

---

### 🔴 #2 — Ollama fallback is silent (tells the user a lie)

**Problem:** `/provider ollama` with ollama down → `enricher.enrich()` swallows the exception and
silently falls back to extraction-only. User believes they got LLM summaries; they got nothing.
See `any2md/enrich/enricher.py:19` (`except Exception: pass`).

**Fix:** make the fallback visible. Options to weigh (ask user if unsure):
- (a) `enrich()` returns/raises-up a flag indicating the summarizer failed, and the REPL prints
  `ollama unreachable — used extractive instead` in `_convert_with_progress`
  (`any2md/repl.py:172`). Keep best-effort: still write the file.
- (b) Simpler: in `repl._convert_with_progress`, before submitting an ollama job, call
  `ollama.available()` (`any2md/enrich/ollama.py:15`) once; if False, warn + transparently use
  extractive for that job.

Recommended: (a) — real signal from the actual call, not a pre-check that can race.

**TDD:** `tests/test_enricher.py` — inject a fake Summarizer whose `summarize` raises; assert the
Document is unchanged AND the failure is signaled (return value / flag). Mock, no network.

---

### 🟡 #3 — Re-converting the same URL makes duplicate notes (vault clutter)

**Problem:** `any2md/writer.py:21` only does collision-suffix (`foo.md`, `foo-2.md`, `foo-3.md`).
Converting the same link twice = two notes. Bad for a canonical Obsidian vault.

**Fix:** dedup by `source_url`. Before writing, scan existing `.md` frontmatter in the output dir
for a matching `source_url`; if found, default to overwrite (or ask overwrite / new-copy / skip).
Keep slug-collision suffix only for genuinely different sources that slug the same.

**TDD:** `tests/test_writer.py` — write a doc, write again with same `source_url`, assert single
file (overwritten), not `-2`. tmp dir, no network. Confirm desired default (overwrite vs ask) with
user first — this changes behavior.

---

### 🟡 #4 — No "where did it go" on first conversion

**Problem:** `repl._convert_with_progress` (`any2md/repl.py:206-210`) prints `job.result.name` +
`/rename` hint, not the full path. New user doesn't know the output folder until `/output`.

**Fix:** print the full path on the **first** conversion of a session; basename thereafter.
Track a "shown full path once" flag on the Repl instance.

**TDD:** logic is in interactive `run`/`_convert_with_progress` (marked `pragma: no cover`).
Extract the "what to display" decision into a small pure helper and unit-test that.

---

### 🟢 #5 — Batch jobs invisible while running

`/batch` (`any2md/repl.py:109`) queues silently; only `/jobs` shows status. Live spinner only wraps
single foreground convert. Optional: a compact live table for queued batch items. Low priority.

### 🟢 #6 — No empty-extraction warning

Paywalled / JS-only page → trafilatura returns near-empty body → a note with frontmatter and no
content, no warning. Add: if `body_markdown` is effectively empty after extract, surface
`extracted almost no content — page may be paywalled or JS-only`. Low priority.

### 🟢 #7 — First-run doesn't surface `/help`

`_first_run` (`any2md/repl.py:148`) + `print_welcome` show the palette but no "type /help anytime"
nudge. One-line add. Low priority.

---

## 4. Recommended order

Do **#1 + #2 first** — they are the real "download and it doesn't work / it lies to me" cases that
violate the core promise. Then **#3** (vault hygiene). #4–#7 are polish.

## 5. Key file map (for these edits)

| Concern | File |
|---|---|
| Local-file / OCR extraction | `any2md/handlers/files.py` |
| YouTube / Whisper fallback | `any2md/handlers/youtube.py` |
| Enrich + best-effort fallback | `any2md/enrich/enricher.py` |
| Ollama summarizer + `available()` | `any2md/enrich/ollama.py` |
| Provider → Summarizer resolve | `any2md/enrich/providers.py` |
| Pipeline orchestration | `any2md/pipeline.py` |
| REPL display / progress / commands | `any2md/repl.py` |
| Slug + collision + `rename_output` | `any2md/writer.py` |
| Frontmatter / body render | `any2md/render.py` |

## 6. How to verify (every edit)

```
source .venv/bin/activate
pytest -q            # full suite, must stay green (currently 152)
ruff check .         # must stay clean
```
A `.claude/hooks/ruff.sh` hook runs ruff on edited `.py` — it strips unused imports, so add the
import in the same edit that uses it. Isolate global state in tests with `ANY2MD_CONFIG` and
`ANY2MD_STATS` env → tmp paths. Mock module-level `_fetch_*` helpers / `shutil.which` / httpx —
never hit the network or real binaries.
