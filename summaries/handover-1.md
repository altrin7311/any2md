# Any2MD — Post-Deployment Handover

Date: 2026-05-30  
Version: 0.1.0  
Author: Altrin Titus

---

## What is live

| Thing | URL / location |
|---|---|
| PyPI package | https://pypi.org/project/any2md-cli/0.1.0/ |
| Railway service | https://any2md-production.up.railway.app |
| GitHub repo | https://github.com/altrin7311/any2md |
| Railway project | efficient-flexibility (project ID: 1588deef-cde6-4c95-bda0-824f8bf06795) |

Install: `pipx install any2md-cli` → command `any2md`

---

## Architecture snapshot

```
input → registry.detect() → handler.extract() → Document
      → enricher.enrich()  (summary/tags/wikilinks)
      → render() → writer.write()   → flat .md in output folder
```

Single async queue shared by REPL (`any2md`) and HTTP server (`any2md serve`).

### Handlers (all keyless, no API keys)
youtube · reddit (rss fallback) · github · hackernews · arxiv · wikipedia · stackoverflow · twitter · web (catch-all) · files (pdf/docx/pptx/xlsx/csv/img/html/epub via markitdown)

### Summarizers
- `extractive` — default, pure-Python TextRank, zero setup
- `ollama` — local model, auto-detected on first run
- `none` — extraction only

---

## HTTP API (serve mode)

Base URL: `https://any2md-production.up.railway.app`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | no | service info + version |
| GET | `/health` | no | liveness check → `{"status":"ok"}` |
| POST | `/convert` | Bearer token | submit URL/path for conversion |
| GET | `/jobs/{id}` | no | poll job status |
| GET | `/jobs/{id}/download` | no | download resulting .md |

Auth header for `/convert`: `Authorization: Bearer <ANY2MD_TOKEN>`

---

## Environment variables (set in Railway dashboard)

| Var | Value | Notes |
|---|---|---|
| `ANY2MD_TOKEN` | your secret | gates POST /convert |
| `ANY2MD_PROVIDER` | `extractive` | safe for Railway (no Ollama needed) |
| `ANY2MD_OUTPUT_DIR` | `/data` | default, set in Dockerfile |

---

## Key files

| File | What it does |
|---|---|
| `any2md/__init__.py` | `__version__` — bump here before every release |
| `pyproject.toml` | `name = "any2md-cli"` — PyPI name (≠ import name) |
| `Dockerfile` | production image: python:3.11-slim + ffmpeg + tesseract |
| `railway.toml` | builder=dockerfile, start command reads `$PORT` from env |
| `.github/workflows/ci.yml` | ruff + pytest on push/PR (Python 3.11 + 3.12) |
| `any2md/handlers/` | one file per source handler |
| `any2md/enrich/` | summarizers (extractive, ollama, none) |
| `any2md/render.py` | Document → .md (golden-file tested) |
| `any2md/server.py` | FastAPI app + queue endpoints |
| `any2md/cli.py` | Typer CLI — REPL + `convert` + `serve` commands |

---

## How to make a change and ship it

### Code change
```bash
# 1. edit code
# 2. run tests
.venv/bin/pytest -q
.venv/bin/ruff check .

# 3. push — Railway auto-redeploys if GitHub is connected
git add <files>
git commit -m "..."
git push
```

### Add a new source handler
```
/new-handler <source>      # scaffolds handler + fixture test via handler-builder agent
```
Handlers live in `any2md/handlers/`. Register in `any2md/registry.py`.

### Release to PyPI
```bash
# 1. bump version
# edit any2md/__init__.py: __version__ = "0.1.1"

# 2. build
rm -rf dist build
python -m build

# 3. upload
twine upload dist/*
# username: __token__
# password: pypi-... (generate fresh token at pypi.org — scope to any2md-cli)
```

---

## Known issues / TODOs

- **Railway GitHub auto-deploy not yet connected** — currently deploys via `railway up` (CLI). To fix: Railway dashboard → Settings → Source → Connect Repo → pick `altrin7311/any2md` → branch `main`. After this, every push auto-redeploys.
- **PyPI token used in session** was pasted in chat — revoke it at pypi.org/manage/account/token/ and generate a new one scoped to `any2md-cli` only.
- **Twitter handler** is best-effort (keyless CDN + derived token) — may break if X changes the endpoint.
- **Reddit handler** uses `.rss` fallback because `.json` returns 403 — functional but lower fidelity than the original JSON API.

---

## Local dev setup

```bash
git clone https://github.com/altrin7311/any2md
cd any2md
uv venv .venv --python 3.11   # or: python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
any2md                         # starts REPL
```

Config lives at `~/.any2md/config.toml`. Test isolation: set `ANY2MD_CONFIG` + `ANY2MD_STATS` env vars to tmp paths.

---

## Rules to not break

- No API keys, ever. All handlers are keyless.
- Summarizer errors must never hard-fail — fall back to extraction-only output.
- No live network in tests — mock `_fetch_*` helpers, use fixtures in `tests/fixtures/`.
- Output frontmatter always includes `source_url`, `source_type`, `extraction_date`.
- Handler contract: `extract()` returns a `Document`, no summarizing, no file writing inside a handler.
