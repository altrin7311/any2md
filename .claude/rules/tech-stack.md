# Rule: Tech stack & tooling

Python project. Prefer `uv` for env/deps; fall back to `pip` + venv.

## Runtime deps (by layer)
| Layer | Library | Notes |
|---|---|---|
| CLI / REPL | `typer`, `rich` | Typer = commands; Rich = progress/output |
| Files handler | `markitdown` | MS, MIT. Covers pdf/docx/pptx/xlsx/csv/img-OCR/html/epub |
| YouTube | `yt-dlp` | metadata + captions; needs `ffmpeg` only for Whisper fallback |
| Reddit | `httpx` | public `.json` endpoint, no API key |
| GitHub | `httpx` | public REST, unauthenticated (60 req/hr) |
| Web | `trafilatura` | readability article extraction |
| Summarize (default) | stdlib only | `extractive` — pure-Python TextRank-style; no model, no network, no deps |
| Summarize (optional) | `httpx` | `ollama` — local model at `OLLAMA_URL`; lazy httpx; no API key |
| Serve | `fastapi`, `uvicorn` | optional; only for `serve` mode |
| Config | stdlib `tomllib` + `tomli-w` | read/write `~/.any2md/config.toml` |

## Dev tooling
- `pytest` — tests. `pytest-recording`/saved fixtures for handler tests (no live network).
- `ruff` — lint + format (the `.claude/hooks/ruff.sh` hook runs it on edited `.py`).
- Target Python 3.11+ (`tomllib` is stdlib from 3.11).

## System deps (for Docker / serve)
- `ffmpeg` — yt-dlp Whisper fallback (only if enabled).
- `tesseract-ocr` — image OCR via markitdown.

## Summarizers (no APIs, no keys)
- `extractive` (default): pure-Python frequency/TextRank-style. Sentences → summary,
  frequent content words → tags, capitalized phrases → `[[wikilinks]]`. Zero setup, Railway-safe.
- `ollama` (optional): local model via `OLLAMA_URL` (default `http://localhost:11434`),
  `OLLAMA_MODEL` (default `llama3.2`). Requires user-run Ollama. No key. Unreachable → falls
  back to extraction-only.
- `none`: extraction only, no summary.

## Env vars (no API keys exist)
`OLLAMA_URL`, `OLLAMA_MODEL` (optional, for the ollama summarizer), `ANY2MD_TOKEN` (gates `serve`).
Config keys also overridable via `ANY2MD_OUTPUT_DIR`, `ANY2MD_PROVIDER`, `ANY2MD_WHISPER_FALLBACK`.

## Config precedence
CLI flag > env var > `~/.any2md/config.toml` > built-in default.
