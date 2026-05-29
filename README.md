# Any2MD

[![CI](https://github.com/altrin7311/any2md/actions/workflows/ci.yml/badge.svg)](https://github.com/altrin7311/any2md/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

Free, open-source CLI that converts almost anything — local files (PDF, DOCX, XLSX, images…)
and online links (YouTube, Reddit, GitHub, arXiv, Wikipedia, Hacker News, Stack Overflow,
Twitter/X, web articles) — into Obsidian-flavored Markdown for a knowledge graph.
Every input is summarized. **No external APIs, no API keys, ever.**

## Install

One command, anywhere (recommended — isolated, no venv to manage):

```bash
pipx install any2md
```

Then just run it:

```bash
any2md
```

The **first run** asks one thing — where to save your `.md` files — and then gets out of the
way. Summaries run locally: if [Ollama](https://ollama.com) is running it's used automatically,
otherwise a built-in zero-setup extractive summarizer is used. Nothing else to configure.

<details><summary>From source (dev)</summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```
</details>

## Usage

### One-shot

```bash
any2md convert https://github.com/karpathy/nanoGPT
any2md convert ~/notes/paper.pdf -o ~/ObsidianVault/inbox
any2md convert https://arxiv.org/abs/1706.03762 --depth high --provider extractive
any2md convert --batch links.txt          # one target per line
```

Re-converting the same link refreshes the existing note instead of making a duplicate (tracking
params like `utm_*` are stripped, so the same article always maps to one note). Pages that extract
to nothing — paywalled or JavaScript-only — are skipped with a warning rather than written as
empty notes.

### Interactive REPL

```bash
any2md            # opens the REPL
```

Inside the REPL, paste a URL or file path to convert it. Commands:

| Command | Effect |
|---|---|
| `/output <dir>` | set output folder |
| `/provider <name>` | set summarizer: `extractive` (default) · `ollama` · `none` |
| `/depth` | how much to keep: `low` · `medium` · `high` · `raw` (◀ ▶ live picker) |
| `/batch <file>` | submit every line in a file |
| `/jobs` | list jobs + status |
| `/last` | path of the last written `.md` |
| `/open [last]` | open the output folder (or the last note) in your file viewer |
| `/rename <name>` | rename the file you just made (slug auto-cleaned) |
| `/help` · `/quit` | help / exit |

While a conversion runs you get a live spinner with an estimated time (it learns your real
timings per source) and a rotating tip. Drag a file straight into the terminal to convert it.

### Config

```bash
any2md config set output ~/ObsidianVault/inbox
any2md config set provider extractive
any2md config show
```

Precedence: CLI flag > env var (`ANY2MD_OUTPUT_DIR`, `ANY2MD_PROVIDER`, …) > `~/.any2md/config.toml` > default.

## Summarizers (all free, offline)

- **`extractive`** (default): pure-Python TextRank-style. Zero setup, no network.
- **`ollama`**: local model via `OLLAMA_URL` (default `http://localhost:11434`),
  `OLLAMA_MODEL` (default `llama3.2`). Unreachable → falls back to extraction-only.
- **`none`**: extraction only, no summary.

## Serve mode (HTTP)

```bash
any2md serve --port 8000
```

Routes:

```bash
# submit a conversion → returns {"id": "..."}
curl -X POST localhost:8000/convert -H 'Content-Type: application/json' \
     -d '{"target":"https://github.com/karpathy/nanoGPT"}'

curl localhost:8000/jobs/<id>            # status + progress
curl localhost:8000/jobs/<id>/download   # the rendered .md
```

Set `ANY2MD_TOKEN` to gate access — clients then send `Authorization: Bearer <token>`.

## Deploy

### Docker

```bash
docker build -t any2md .
docker run -p 8000:8000 -e ANY2MD_TOKEN=secret -v "$PWD/data:/data" any2md
```

### Railway

Push the repo; Railway builds the `Dockerfile` and runs `any2md serve` on `$PORT`
(see `railway.toml`). Set `ANY2MD_TOKEN` and `ANY2MD_PROVIDER=extractive` in the dashboard.
No API keys required — the stack is fully free/offline.

## Develop

```bash
pytest -q          # tests (no live network)
ruff check .       # lint
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow (TDD, fixtures, adding a source).
CI runs the suite + lint on every push and PR.

### Publish to PyPI (maintainer)

`pipx install any2md` works once the package is on PyPI. To cut a release:

```bash
python -m build                 # builds dist/*.whl and dist/*.tar.gz
twine upload dist/*             # needs your PyPI account / API token
```

Bump `__version__` in `any2md/__init__.py` first (`pyproject.toml` reads it dynamically).
