# Any2MD — Design Spec

**Date:** 2026-05-28
**Status:** Approved (brainstorming complete, pre-implementation)

## 1. Purpose

A free, open-source tool that converts almost anything — local files (PDF, DOCX,
XLSX, PPTX, images, HTML, EPUB…) and online sources (YouTube, Reddit, GitHub,
generic web articles) — into Obsidian-flavored Markdown `.md` files, for ingestion
into a Karpathy-style Obsidian knowledge graph.

Primary interface is a **CLI** (Claude-Code-style: interactive REPL + scriptable
one-shot commands). An optional `serve` mode exposes the same pipeline over HTTP
for Docker/Railway deployment.

### Goals
- Convert the **Core 6** source classes (see §4) to clean Obsidian Markdown.
- **Summarize every input** (quality is a priority — no degraded output).
- 100% free / open-source. No paid APIs or paid hosting tiers required.
- Production-ready: Dockerized, optionally deployable to Railway.

### Non-Goals (MVP)
- Sources beyond the Core 6 (Twitter/X, HN, Stack Overflow, Wikipedia, arXiv,
  podcasts, RSS, etc.) — designed for, but deferred to later releases.
- A rich web UI. `serve` mode is a minimal HTTP API only.
- Bundling a local LLM (Ollama) inside the shipped container.

## 2. Constraints & Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Output format | Obsidian Markdown: YAML frontmatter + body + `#tags` + `[[wikilinks]]` | Feeds Karpathy-style Obsidian graph |
| Output layout | Flat, slugified filenames in one folder | Obsidian graph prefers flat; configurable folder |
| Frontmatter must include | `source_url`, `source_type`, `extraction_date`, `upload_date` | User requirement: track source + dates |
| Summaries | Every input summarized | Quality priority |
| LLM | Pluggable provider (Groq / Gemini / Cloudflare / Ollama / none) | Free tiers; `none` = extraction-only fallback |
| Default LLM | Groq (open-weight Llama, fast, free tier) | Best free quality/speed; open-weight matches OSS goal |
| Interface | CLI: REPL + one-shot subcommands | Claude-Code-style flexibility |
| Processing | Async job queue | Long jobs (YouTube/transcription) survive without timeout |
| Deploy | CLI primary + optional `serve` mode → Docker → Railway | CLI is the product; serve is a bonus |
| Stack | Python + Typer + Rich | markitdown/yt-dlp/praw are Python; Typer+Rich for CLI/REPL |
| Architecture | Layered pipeline + handler registry (Approach A) | Clean per-source isolation, shared enrichment, grows into plugins |

### Railway / free-tier strategy
The shipped container is **lightweight** (extraction only). LLM summarization is
delegated to a **free-tier hosted LLM API** (open-weight models via Groq, etc.)
configured by the user's own free API key (env var). This keeps Railway within
free/hobby limits and yields higher quality than a tiny self-hosted model. Ollama
remains supported for users who run it on their own hardware (`LLM_PROVIDER=ollama`,
`OLLAMA_URL`).

## 3. Architecture (Approach A: layered pipeline + handler registry)

### Module layout
```
any2md/
├── cli.py            # Typer app: REPL + one-shot subcommands
├── repl.py           # interactive session, slash-commands
├── pipeline.py       # orchestrates: detect→extract→normalize→enrich→render→write
├── registry.py       # handler lookup by URL pattern / file extension
├── models.py         # Document dataclass (internal normalized form)
├── config.py         # ~/.any2md/config.toml load/save, env overrides
├── queue.py          # async job queue + progress events
├── handlers/
│   ├── base.py       # Handler ABC: matches() + extract() -> Document
│   ├── files.py      # markitdown: pdf/docx/xlsx/pptx/img/html/epub/...
│   ├── youtube.py    # yt-dlp: metadata + subtitles (Whisper fallback)
│   ├── reddit.py     # post + top 20 comments (nested)
│   ├── github.py     # README + repo metadata
│   └── web.py        # readability article extraction (catch-all fallback)
├── enrich/
│   ├── base.py       # LLMProvider ABC
│   ├── groq.py / gemini.py / cloudflare.py / ollama.py
│   └── enricher.py   # summary + tags + [[wikilinks]] from Document
├── render.py         # Document -> Obsidian markdown string
├── writer.py         # slugify, collision-suffix, write to output folder
└── server.py         # optional FastAPI `serve` mode (reuses pipeline+queue)
```

### Pipeline (one path for everything)
```
input (url|file)
  → registry.detect()    picks handler (specialized first, web fallback last)
  → handler.extract()    → Document (raw, normalized)
  → enricher.enrich()    adds summary, tags, wikilinks (skipped gracefully if no LLM)
  → render()             Document → Obsidian .md string
  → writer.write()       slug.md in output folder
```

### `Document` data model (contract between layers)
```python
@dataclass
class Document:
    title: str
    source_url: str | None      # None for local files
    source_type: str            # youtube|reddit|github|web|pdf|docx|...
    upload_date: str | None     # publish/upload date if the source has one
    extraction_date: str        # now()
    body_markdown: str          # extracted content
    metadata: dict              # type-specific extras (channel, stars, subreddit...)
    # filled by enricher:
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
```

## 4. Handlers (Core 6)

```python
class Handler(ABC):
    @abstractmethod
    def matches(self, target: str) -> bool: ...   # url regex or file ext
    @abstractmethod
    def extract(self, target: str) -> Document: ...
```

Registry tries handlers in priority order; `web.py` is the catch-all fallback for
any URL no specialized handler claims.

| Handler | Tool / source | Notes |
|---|---|---|
| `files` | `markitdown` (MS, MIT) | One lib: pdf/docx/pptx/xlsx/img-OCR/html/epub/csv. Image vision description added in enrich step if LLM is vision-capable. |
| `youtube` | `yt-dlp` | Metadata + existing captions (free, fast). Whisper only as fallback when no captions exist — **off by default** (`whisper_fallback`) to stay Railway-light. |
| `reddit` | public `.json` endpoint | No API key. Post + top 20 comments by score, nested. |
| `github` | public REST (unauthenticated) | README + stars/topics/license/languages/dates. 60 req/hr unauth is plenty. |
| `web` | `trafilatura` / readability-lxml | Clean article extraction. Catch-all for unmatched URLs. |

## 5. LLM enrichment

```python
class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, *, system: str = "") -> str: ...
    def describe_image(self, path: str) -> str | None: ...  # optional, vision models
```

- `LLM_PROVIDER=groq|gemini|cloudflare|ollama|none`. Each provider reads its own
  key env var (`GROQ_API_KEY`, etc.).
- `none` = extraction-only mode: transcripts/OCR/metadata still produced, no
  summary/tags/wikilinks. **App never hard-fails on a missing key.**
- `enricher.enrich(doc)` produces, in one or few calls:
  - **summary** — concise summary of `body_markdown` (always).
  - **tags** — 3–8 topical `#tags`.
  - **wikilinks** — key entities/concepts wrapped as `[[...]]` for graph connectivity.
  - Long inputs chunked, or sent whole on large-context providers (Gemini 1M).

## 6. CLI

**One-shot (scriptable):**
```
any2md convert <url|file> [-o FOLDER]
any2md convert --batch links.txt [-o FOLDER]
any2md config set output ~/ObsidianVault/inbox
any2md config set provider groq
any2md serve [--port 8000]
```

**REPL (`any2md` with no args → Claude-Code-style session):**
```
> https://youtube.com/watch?v=...     # paste link → converts
> ./report.pdf                         # path → converts
/output ~/vault/inbox                  # change output folder
/provider gemini                       # switch LLM
/batch links.txt                       # bulk
/jobs                                  # show running/queued jobs
/last                                  # reopen last output path
/help   /quit
```
Rich shows live per-job progress (extract → enrich → write).

## 7. Config

`~/.any2md/config.toml`:
```toml
output_dir = "~/ObsidianVault/inbox"
provider   = "groq"
whisper_fallback = false        # youtube w/o captions
[providers.groq]
model = "llama-3.3-70b-versatile"
```
API keys come from **env vars only** (never written to the config file).
Precedence: CLI flag > env var > `config.toml` > built-in default.

## 8. Async queue

`queue.py` = `asyncio` task queue + worker pool. The CLI REPL and the FastAPI
`serve` mode both submit jobs to it and subscribe to progress events. One engine,
two front-ends — no duplicated logic.

## 9. `serve` mode + Docker + Railway

- `server.py` (FastAPI):
  - `POST /convert` (url/file) → job id
  - `GET /jobs/{id}` → status / progress
  - `GET /jobs/{id}/download` → `.md`
- **Dockerfile**: `python-slim` base + system deps (`ffmpeg` for yt-dlp, `tesseract`
  for OCR). `ENTRYPOINT any2md`.
- **Railway**: `railway.toml`, start command `any2md serve --port $PORT`.
  A single shared password env (`ANY2MD_TOKEN`) gates `serve` so a public deploy
  cannot burn the owner's free LLM quota. Local CLI use needs no auth.

## 10. Output example (`how-to-build-x.md`)

```markdown
---
title: "How to Build X"
source_url: "https://youtube.com/watch?v=abc"
source_type: youtube
upload_date: 2026-05-01
extraction_date: 2026-05-28
channel: "Some Channel"
tags: [ai, tutorial, systems]
---

# How to Build X

> **Summary:** <LLM summary here>

Key concepts: [[Embeddings]], [[Vector Search]], [[RAG]]

## Transcript
<full transcript / extracted body>
```

## 11. Testing strategy (TDD)

- **Per handler:** `extract()` tested against a saved fixture (recorded
  HTML/JSON/sample file) → asserts `Document` fields. No live network in tests.
- **Enricher:** LLM provider mocked; tested with a fake provider returning canned
  summary/tags/wikilinks.
- **Render:** golden-file test (Document → expected `.md`).
- **Writer:** slug + collision-suffix tests.
- **End-to-end:** one test per source through the full pipeline with mocked
  external calls.

## 12. Open items / future

- Additional source handlers (Twitter/X, HN, Stack Overflow, Wikipedia, arXiv,
  Medium/Substack, RSS, podcasts via Whisper) — add as new `Handler` modules.
- Possible migration to plugin entry-points (Approach B) once the handler set
  grows or community contributions arrive.
