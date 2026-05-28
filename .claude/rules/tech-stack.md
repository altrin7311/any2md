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
| LLM | provider SDKs / `httpx` | groq, google-genai, cloudflare, ollama — lazy-imported per provider |
| Serve | `fastapi`, `uvicorn` | optional; only for `serve` mode |
| Config | stdlib `tomllib` + `tomli-w` | read/write `~/.any2md/config.toml` |

## Dev tooling
- `pytest` — tests. `pytest-recording`/saved fixtures for handler tests (no live network).
- `ruff` — lint + format (the `.claude/hooks/ruff.sh` hook runs it on edited `.py`).
- Target Python 3.11+ (`tomllib` is stdlib from 3.11).

## System deps (for Docker / serve)
- `ffmpeg` — yt-dlp Whisper fallback (only if enabled).
- `tesseract-ocr` — image OCR via markitdown.

## Env vars (keys never go in config.toml)
`GROQ_API_KEY`, `GEMINI_API_KEY`, `CLOUDFLARE_API_TOKEN`+`CLOUDFLARE_ACCOUNT_ID`,
`OLLAMA_URL`, `ANY2MD_TOKEN` (gates `serve`).

## Config precedence
CLI flag > env var > `~/.any2md/config.toml` > built-in default.
