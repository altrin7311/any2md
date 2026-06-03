# Any2MD — Usability Fixes: Remote Files · Ollama Autostart · Sticky Output

Date: 2026-06-01
Author: Altrin Titus (design w/ Claude)
Status: Approved — ready for implementation plan

---

## Context

Three day-to-day usability failures reported from real use of the shipped CLI:

1. **A direct link to a PDF fails to convert.** Example:
   `https://cdn.prod.website-files.com/.../The-Founders-Playbook-05062026_v3%20(1).pdf`
   produced `⚠ extraction failed — source may be empty, paywalled, or JS-only; nothing written`.
2. **Ollama is "always unreachable"** and must be started manually. The user wants it to boot
   automatically whenever the CLI (REPL or one-shot) runs.
3. **The output directory is not remembered** — it must be re-entered on every start.

### Root causes (confirmed)

1. **No remote-file ingestion.** `FilesHandler.matches` explicitly returns `False` for any
   `http(s)://` target (`any2md/handlers/files.py:42-43`), so a `.pdf` URL is not claimed by the
   files handler. It falls through every specialized handler to the **`WebHandler`** catch-all,
   which runs `trafilatura` — trafilatura cannot parse a binary PDF, returns an empty body, and
   the pipeline skips with the generic "extraction failed" message. Verified:
   `registry.detect(<pdf url>)` → `WebHandler`. The URL's `%20` / `(1)` are URL-encoding; after
   `urllib.parse.unquote` the suffix is cleanly `.pdf`.
2. **Ollama is never auto-started, and the failure message is misleading.** `ollama.available()`
   works, but nothing launches `ollama serve` when it is down. Worse, `OllamaSummarizer.summarize`
   raises for *any* failure (server down **or** model not pulled), and `enrich_with_fallback`
   reports the single hardcoded string `"ollama unreachable — used extractive instead"` for all
   of them — so a missing model reads as "unreachable". Provider also only becomes `ollama` if the
   server happened to be running at first-run (`onboarding.apply_first_run`).
3. **`/output` does not persist.** The REPL `/output <dir>` command sets `self.output_dir` but —
   unlike `/provider` and `/depth` — never calls `config.set_value` (`any2md/repl.py:199-203`).
   First-run onboarding *does* persist the dir, so the gap is specifically a later `/output`
   change being lost on restart.

---

## Goals & success criteria

- **Remote files convert:** a direct `http(s)` link to any markitdown-supported document
  (pdf, docx, pptx, xlsx, csv, html, epub, txt, images) downloads and converts exactly like the
  local file would, with `source_url` set and the correct `source_type`. Download failures
  produce a clean skip, never a traceback.
- **Ollama is hands-off:** launching any2md auto-starts `ollama serve` when ollama is installed
  but down; the model is ensured (ask-once consent before a large pull); messages distinguish
  not-installed / starting / model-missing / unreachable. The user never starts ollama manually.
- **Output dir is sticky:** setting `/output <dir>` persists across restarts; the active dir is
  shown at startup.
- **No regressions:** `pytest -q` + `ruff check .` stay green; no live network in tests.

## Hard constraints (unchanged)

- 100% free / open-source, **no API keys, ever**. (Ollama is a local process, not an API key.)
- Summarization stays best-effort: ollama failure always degrades to extractive/extraction-only.
- Output frontmatter always includes `source_url`, `source_type`, `extraction_date`.
- No live network in tests — mock `_fetch_*` / subprocess / httpx; use fixtures.
- Handlers do extraction only — no summarizing, no file writing.

---

## Component A — Remote file ingestion

**Decision: a new `RemoteFileHandler`, ordered immediately before `WebHandler`** (the catch-all
stays last). Rejected alternatives: extending `FilesHandler` to accept URLs (muddies the
"local file" unit and its matching), and sniffing PDFs inside `WebHandler` (pollutes the
catch-all).

`any2md/handlers/remote_file.py`:
- `matches(target)`: `target` is `http(s)://` **and** the `unquote`d URL path suffix is in the
  known document-extension set (reuse / share `files._SOURCE_TYPE`). For extension-less URLs,
  matching stays cheap (suffix only) — content-type sniffing happens in `extract`, not `matches`
  (matching must be side-effect free per the handler contract).
- `extract(target)`:
  - Download via a module-level `_download(url) -> Path` helper (mockable): `httpx` stream,
    `follow_redirects=True`, timeout, **size cap** (default 50 MB) to a `tempfile`, preserving the
    suffix. On `httpx.HTTPError` / oversize → raise `SourceUnavailable` (clean skip).
  - For an extension-less but matched-by-content URL: sniff `Content-Type`
    (`application/pdf`, the office `openxmlformats` types, `text/html`, …) to pick the suffix.
  - Run `markitdown` on the temp file (same call path as `FilesHandler`), then delete the temp
    file (`finally`).
  - Return a `Document` with `source_url = target`, `source_type` = the resolved type
    (`pdf`/`docx`/…), `title` from markitdown or the `unquote`d filename stem.
- `source_type` class attr: `"remotefile"` (eta classification); the emitted `Document.source_type`
  is the concrete file type so frontmatter/rendering match the local-file behavior.

Registry order becomes: …specialized…, `FilesHandler` (local), `RemoteFileHandler`, `WebHandler`.

## Component B — Ollama autostart

New module-level helpers in `any2md/enrich/ollama.py`:

- `ensure_ready(interactive: bool) -> str` — the single entry point. Returns the provider to use
  (`"ollama"` when ready, else `"extractive"`). Steps:
  1. `shutil.which("ollama") is None` → return `"extractive"` (no nag, no spawn).
  2. server reachable (`available()`) → go to model check.
  3. else spawn `ollama serve` **detached** (`subprocess.Popen`, `start_new_session=True`,
     stdout/stderr to devnull), then poll `available()` up to ~15s. Unreachable after that →
     return `"extractive"` with an accurate "couldn't start ollama" note.
- `_ensure_model(interactive) -> bool` — query `/api/tags`:
  - `OLLAMA_MODEL` present in the list → ok.
  - else if any model is already pulled → use the first (set the session model) — never force a
    download when a usable model exists.
  - else **ask once** (only when `interactive`): `Pull llama3.2 (~2GB)? [y/N]`. Persist the answer
    in a new config key `ollama_autopull` (bool). `y` → `ollama pull <model>` streaming progress;
    `n` / non-interactive → return False, use extractive this session, print the exact
    `ollama pull <model>` command.
- **Accurate messaging:** replace the blanket `"ollama unreachable — used extractive instead"` in
  `enrich_with_fallback` with the specific reason surfaced by `ensure_ready`/`_ensure_model`
  (not-installed · started · model-missing · unreachable).

Wiring:
- REPL: call `ensure_ready(interactive=sys.stdin.isatty())` at startup (before the banner) when
  the resolved provider is `ollama`; update `self.provider` from the result.
- One-shot `convert` (`cli.py`): call `ensure_ready(interactive=…)` before converting when the
  resolved provider is `ollama`.
- First-run preference (`onboarding.apply_first_run`): prefer `ollama` when it is **installed**
  (not only already-running), since autostart can bring it up. An explicit later `/provider`
  choice stays sticky.

New config key: add `ollama_autopull` to `config.DEFAULTS` (default unset/None → "ask") so
`config._canonical` accepts it.

## Component C — Sticky output dir

- `any2md/repl.py` `/output <dir>`: add `config.set_value("output_dir", _clean_dropped_path(arg))`
  alongside setting `self.output_dir` (mirrors `/provider` and `/depth`).
- Show the active output dir in the startup banner (`theme.print_welcome` or the REPL header) so
  it is visible without running `/output`.
- Onboarding persistence is already correct — unchanged.

---

## Error handling

- Remote download / oversize / unsupported content-type → `SourceUnavailable(reason)` →
  `pipeline.convert` emits `warn:skipped: <reason>` and returns `None` (the graceful-skip path
  shared with the 2026-05-30 spec). No traceback reaches the user.
- Ollama spawn failure, server-never-ready, or model-missing → degrade to extractive with an
  accurate one-line note; conversion always still succeeds (best-effort constraint).

## Testing (TDD, no live network)

- **A:** unit test `RemoteFileHandler.matches` (pdf/docx URLs match, `%20`/`(1)` decode, plain web
  URL does not). `extract` test mocks `_download` to return a fixture file path → asserts
  `source_type`, `source_url`, title, temp cleanup. `registry` test: `.pdf` URL routes to
  `RemoteFileHandler`, not `WebHandler`. Download-failure test → `SourceUnavailable` → clean skip.
- **B:** mock `shutil.which`, `subprocess.Popen`, and `httpx`: assert spawn-when-down, no-op when
  already-running or not-installed, poll-until-ready, give-up path. `_ensure_model`: present /
  fallback-to-existing / ask-once-consent-persists / non-interactive paths. Assert the accurate
  message strings.
- **C:** `repl.handle("/output X")` writes to an isolated `ANY2MD_CONFIG`; a fresh `Repl` reads it
  back. Banner shows the dir.
- Full suite + ruff green; existing `render()` golden tests unchanged.

## Out of scope

- PDF *text-quality* cleanup (glued words, author-block boilerplate) — owned by the 2026-05-30
  quality-overhaul spec.
- Authenticated / paywalled / JS-only sources.
- Non-file URL types beyond the existing handlers.
- Bundling or installing Ollama itself, or pulling models without consent.

## Relationship to other specs

Complements `2026-05-30-quality-robustness-overhaul-design.md` (summary quality + handler
robustness). The only shared piece is the `SourceUnavailable` → clean-skip path; if that spec
lands first, this one reuses it, otherwise this spec introduces it. Independent otherwise.

## Phasing (suggested)

1. Component C (sticky output) — one-liner + banner; immediate quality-of-life win.
2. Component A (remote files) — unblocks the reported PDF-link failure.
3. Component B (ollama autostart) — most moving parts (subprocess, polling, consent).
