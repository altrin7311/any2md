# Rule: Tech stack & tooling

Python project. Prefer `uv` for env/deps; fall back to `pip` + venv.

## Runtime deps (by layer)
| Layer | Library | Notes |
|---|---|---|
| CLI / REPL | `typer`, `rich` | Typer = commands; Rich = progress/output |
| Files handler | `markitdown` | MS, MIT. Covers pdf/docx/pptx/xlsx/csv/img-OCR/html/epub |
| YouTube | `yt-dlp` | metadata + captions; needs `ffmpeg` only for Whisper fallback |
| Reddit | `httpx` | public `.json` (now 403-blocked) → `.rss` Atom fallback, no key |
| GitHub | `httpx` | public REST, unauthenticated (60 req/hr) |
| Hacker News | `httpx` | Firebase API `hacker-news.firebaseio.com`, no key |
| arXiv | `httpx` + stdlib XML | `export.arxiv.org/api/query` Atom (use https + follow_redirects) |
| Wikipedia | `httpx` | REST `…/api/rest_v1/page/summary/<title>`, no key |
| Stack Overflow | `httpx` | Stack Exchange API `api.stackexchange.com`, no key |
| Twitter/X | `httpx` | keyless `cdn.syndication.twimg.com` + derived token; single tweet |
| Web | `trafilatura` | readability article extraction (catch-all, tried last) |
| Summarize (default) | stdlib only | `extractive` — pure-Python TextRank-style; no model, no network, no deps |
| Summarize (optional) | `httpx` | `ollama` — local model at `OLLAMA_URL`; lazy httpx; no API key |
| Serve | `fastapi`, `uvicorn` | optional (`[serve]` extra); only for `serve` mode |
| CLI theme | `rich` | `theme.py` cyan→purple gradient banner, command palette, tip pools |
| ETA | stdlib `json` | `eta.py` per-source estimate, learns into `~/.any2md/stats.json` |
| Onboarding | — | `onboarding.py`: first run asks output dir, auto-detects Ollama |
| Config | stdlib `tomllib` + `tomli-w` | read/write `~/.any2md/config.toml`; `is_first_run()` |

## Distribution
- Packaged for **pipx/PyPI**: `pyproject.toml` carries metadata + classifiers; MIT `LICENSE`.
- Users: `pipx install any2md` then `any2md`. Maintainer release: `python -m build` + `twine upload`.

## Dev tooling
- `pytest` — tests. Saved fixtures for handler tests (no live network); mock `_fetch_*` helpers.
- `ruff` — lint + format (the `.claude/hooks/ruff.sh` hook runs it on edited `.py`).
- `build` + `twine` — packaging/publish. Target Python 3.11+ (`tomllib` is stdlib from 3.11).

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
`OLLAMA_URL`, `OLLAMA_MODEL` (optional, for the ollama summarizer; also auto-detected on first
run), `ANY2MD_TOKEN` (gates `serve`). Config keys also overridable via `ANY2MD_OUTPUT_DIR`,
`ANY2MD_PROVIDER`, `ANY2MD_WHISPER_FALLBACK`. Test isolation: `ANY2MD_CONFIG` (config path),
`ANY2MD_STATS` (ETA stats path).

## Config precedence
CLI flag > env var > `~/.any2md/config.toml` > built-in default.
