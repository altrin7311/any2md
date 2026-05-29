# Design — Any2MD UX fixes (#1 #2 #3 #4 #6 #7)

> Source: `summaries/2026-05-29-ux-improvements-handover.md`. This spec covers the agreed
> scope (Core + cheap polish). **#5 (batch live table) is out of scope.**
> Hard constraints still apply: 100% free/OSS, no external APIs/keys, summarization is
> best-effort (never hard-fail over enrichment), TDD per change, no live network/binaries in tests.

## Goal

Stop the CLI from (a) crashing cryptically when a system binary is missing, (b) lying that it
used Ollama when it silently didn't, (c) cluttering the vault with duplicate notes for the same
URL, and (d) leaving new users unsure where files went or that `/help` exists. All degradations
become **visible, terminal-only warnings** — never silent, never fatal.

## Decisions (locked with user)

- **Scope:** #1, #2, #3, #4, #6, #7. Skip #5.
- **Dedup (#3):** same `source_url` → **overwrite** the existing note in place.
- **Ollama down (#2):** degrade to the **extractive** summarizer (note still gets a summary) + warn.
- **Warnings surface:** **terminal only** (REPL and one-shot CLI). Not written into the `.md`.
- **Warning channel:** ride the existing `on_event` callback with a `warn:` string prefix —
  adding an `on_warning` param would break the `convert_fn` fakes in `test_queue.py` /
  `test_repl.py`. Stringly-typed but surgical; documented as a convention in `queue.py`.
- **Non-image file conversion failure (#1):** only **images** degrade-to-empty (the tesseract
  case). A corrupt PDF/docx still **raises** → the queue reports a real `✗ error`. We do not
  write contentless junk notes for genuinely broken files.

---

## Architecture: one warnings channel

The three "degrade gracefully" edits (#1 missing binary, #2 ollama down, #6 empty page) share one
shape: *append a soft warning, never raise.* One backbone serves all three.

1. **`Document.warnings: list[str]`** — new field, `field(default_factory=list)`, placed after the
   existing defaulted fields (`summary`, `tags`, `wikilinks`). Not rendered → golden files unchanged.
2. **Producers append to `doc.warnings`:** handlers (`files.py`, `youtube.py`) on degradation; the
   enricher fallback (#2); the empty-content check (#6). None of them raise.
3. **`pipeline.convert` forwards them:** after `enrich_with_fallback`, before returning:
   ```python
   for w in doc.warnings:
       emit("warn:" + w)
   ```
4. **`queue._run`'s `on_event` closure splits them:**
   ```python
   def on_event(stage: str) -> None:
       if stage.startswith("warn:"):
           job.warnings.append(stage[len("warn:"):])
       else:
           job.status = stage
           job.events.append(stage)
   ```
   `Job` gains `warnings: list[str] = field(default_factory=list)`. No `convert_fn` signature
   change → existing fakes stay green.
5. **Display:**
   - REPL `_convert_with_progress`: after the `✓` line, print each `job.warnings` entry dim/amber.
   - `cli.convert`: pass an `on_event` collector that strips the `warn:` prefix and prints the
     warnings after `✓ wrote …`.

---

## Per-edit detail

### #1 — Detect missing system binaries (`any2md/handlers/files.py`, `any2md/handlers/youtube.py`)

**files.py** — `FilesHandler.extract`:
- Compute `source_type` as today.
- If `source_type == "image"`:
  - If `shutil.which("tesseract") is None`: append warning
    `install tesseract for image OCR: brew install tesseract`.
  - Wrap `self._md.convert(target)` in `try/except Exception`; on failure return a Document with
    `body_markdown=""` (degrade — **do not re-raise** for images).
- If `source_type != "image"`: call `self._md.convert(target)` as today (exceptions propagate →
  queue reports a real error).

**youtube.py** — `YouTubeHandler.extract`:
- Captions path is unchanged (needs no ffmpeg).
- At the no-captions branch (`captions` is empty), if `shutil.which("ffmpeg") is None`, append
  warning `no captions found; install ffmpeg for audio transcription`. (The handler has no Whisper
  code today — body already falls back to `description`; this only adds the guard + warning, it
  does not add Whisper.)

### #2 — Ollama silent fallback (`any2md/enrich/enricher.py`, `any2md/pipeline.py`)

- Change `enrich(doc, summarizer) -> bool`:
  - `summarizer is None` → return `True` (no-op success).
  - success → return `True`.
  - `except Exception:` → return `False` (doc left unchanged — still best-effort).
- Add `enrich_with_fallback(doc, provider: str) -> None` in `enricher.py` (isolated, unit-testable):
  ```python
  from any2md.enrich.providers import get_summarizer

  def enrich_with_fallback(doc, provider):
      if not enrich(doc, get_summarizer(provider)) and provider == "ollama":
          doc.warnings.append("ollama unreachable — used extractive instead")
          enrich(doc, get_summarizer("extractive"))
  ```
- `pipeline.convert` calls `enrich_with_fallback(doc, provider)` instead of bare `enrich(...)`.

### #3 — Dedup by `source_url` → overwrite (`any2md/writer.py`)

- New helper `_find_by_source_url(directory, source_url) -> Path | None`: scan `directory/*.md`,
  read each file's frontmatter block, return the first whose `source_url:` line matches. Linear
  scan (YAGNI — no index).
- `write(doc, output_dir)`:
  - If `doc.source_url`: `existing = _find_by_source_url(out, doc.source_url)`; if found, write
    `render(doc)` to `existing` (preserves a `/rename`d filename) and return it.
  - Else (no match, or `source_url is None` for local files): current `_unique` slug + `-2` suffix
    behavior, unchanged.

### #4 — Full path on first conversion (`any2md/repl.py`)

- Pure helper `display_name(path: Path, shown_full_already: bool) -> str`: returns `str(path)` when
  `not shown_full_already`, else `path.name`. Unit-tested.
- `Repl.__init__` sets `self._shown_full_path = False`. `_convert_with_progress` uses the helper for
  the `✓` line and flips the flag to `True` after the first success.

### #6 — Empty-extraction warning (`any2md/pipeline.py`)

- Helper `is_low_content(body: str) -> bool` → `len(body.strip()) < 50`. Unit-tested.
- In `convert`, after `extract`: if `is_low_content(doc.body_markdown)`, append warning
  `extracted almost no content — source may be empty, paywalled, or JS-only`.

### #7 — `/help` nudge (`any2md/theme.py`)

- In `print_welcome`, change the closing hint to include a nudge, e.g.
  `Paste or drag in a link or file to convert it.  ·  type /help anytime`.

---

## Testing (TDD — write the test first, watch it fail, implement)

No live network, no real binaries. Mock `shutil.which`, `MarkItDown.convert`, `get_summarizer`.

| Edit | Test file | Assertion |
|---|---|---|
| backbone | `tests/test_queue.py` | a `warn:`-prefixed `on_event` lands in `job.warnings`, NOT `job.events`; existing stage-order test stays green |
| backbone | `tests/test_render.py` | a Document with `warnings=[...]` renders byte-identical to the existing golden (warnings never leak into output) |
| #1 | `tests/test_files.py` | `shutil.which`→None + `MarkItDown.convert` raises → `extract()` returns a Document, `body_markdown == ""`, tesseract warning in `doc.warnings`, no exception |
| #2 | `tests/test_enricher.py` | raising fake summarizer → `enrich()` returns `False`, doc untouched; `enrich_with_fallback(doc, "ollama")` with raising ollama + working extractive → summary set + warning appended |
| #3 | `tests/test_writer.py` | same `source_url` twice → ONE file, content overwritten, no `-2`; same title + different `source_url` → `-2`; local file (`source_url is None`) twice → `-2` (no dedup) |
| #4 | `tests/test_repl.py` | `display_name(p, False) == str(p)`; `display_name(p, True) == p.name` |
| #6 | (writer/pipeline test module) | `is_low_content("")` and short string True; long string False |
| #7 | `tests/test_theme.py` | `print_welcome` output (captured via a recording `Console`) contains `/help` |

Verify after every edit:
```
source .venv/bin/activate
pytest -q          # must stay green (currently 152, will grow)
ruff check .       # must stay clean
```

## Files touched

`any2md/models.py` (warnings field) · `any2md/queue.py` (Job.warnings + split) ·
`any2md/pipeline.py` (forward warnings, fallback call, empty-content check) ·
`any2md/enrich/enricher.py` (bool return + `enrich_with_fallback`) ·
`any2md/handlers/files.py` (#1 image/tesseract) · `any2md/handlers/youtube.py` (#1 ffmpeg) ·
`any2md/writer.py` (#3 dedup) · `any2md/repl.py` (#4 display_name + warning print) ·
`any2md/cli.py` (warning print in one-shot) · `any2md/theme.py` (#7 nudge).

## Out of scope

- #5 (live batch table).
- Persisting warnings into note frontmatter (chose terminal-only).
- Ollama `available()` precheck (chose real-signal fallback in #2).
- Adding Whisper transcription to youtube (only the ffmpeg guard).

## Notes for the implementer

- User commits/pushes themselves — **do not commit**. Show run commands wrapped as `||command||`.
- `.claude/hooks/ruff.sh` strips unused imports on edited `.py` — add an import in the same edit
  that uses it.
- Isolate global state in tests with `ANY2MD_CONFIG` / `ANY2MD_STATS` → tmp paths.
