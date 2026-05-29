# Any2MD

Free, open-source CLI that converts almost anything — local files (PDF, DOCX, XLSX, images…)
and online links (YouTube, Reddit, GitHub, web articles) — into Obsidian-flavored Markdown
for a knowledge graph. Every input is summarized. **No external APIs, no API keys, ever.**

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

### One-shot

```bash
any2md convert https://github.com/karpathy/nanoGPT
any2md convert ~/notes/paper.pdf -o ~/ObsidianVault/inbox
any2md convert --batch links.txt          # one target per line
```

### Interactive REPL

```bash
any2md            # opens the REPL
```

Inside the REPL, paste a URL or file path to convert it. Commands:

| Command | Effect |
|---|---|
| `/output <dir>` | set output folder |
| `/provider <name>` | set summarizer: `extractive` (default) · `ollama` · `none` |
| `/batch <file>` | submit every line in a file |
| `/jobs` | list jobs + status |
| `/last` | path of the last written `.md` |
| `/help` · `/quit` | help / exit |

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
