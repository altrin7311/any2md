# Rule: Handler & Document contract

The contract every layer depends on. Load this instead of re-reading the spec.

## Document (internal normalized form)
```python
@dataclass
class Document:
    title: str
    source_url: str | None      # None for local files
    source_type: str            # youtube|reddit|github|web|pdf|docx|pptx|xlsx|image|html|epub
    upload_date: str | None     # publish/upload date (ISO) if the source has one
    extraction_date: str        # now(), ISO date
    body_markdown: str          # extracted content (markdown)
    metadata: dict              # type-specific extras: channel, stars, subreddit, author...
    # filled by enricher (None/empty until enrich runs):
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
```

## Handler (one per source)
```python
class Handler(ABC):
    source_type: str = "unknown"           # stable label; used by eta.classify before extract
    @abstractmethod
    def matches(self, target: str) -> bool: ...   # url regex OR file extension
    @abstractmethod
    def extract(self, target: str) -> Document: ...
```

Rules:
- A handler does **extraction only** — no summarizing, no file writing. It returns a `Document`.
- Set the `source_type` class attr (e.g. `"reddit"`); `eta.py` reads it to estimate time
  before `extract()` runs, and it should match the `Document.source_type` you emit.
- `matches()` must be cheap and side-effect free (regex / suffix check).
- Network lives behind module-level `_fetch_*` helpers so tests can mock them (no live net).
  If a primary endpoint can be blocked (Reddit `.json` → 403), catch `httpx.HTTPError` and
  fall back to a keyless alternative (Reddit → `.rss`). Best-effort beats a crash.
- Registry tries handlers in priority order; **`web` is the catch-all fallback** and must be
  tried last. Specialized URL handlers (youtube/reddit/github/hackernews/arxiv/wikipedia/
  stackoverflow/twitter) come first, then files, then web.
- Local-file handlers match by extension; URL handlers match by host/path regex.
- Populate `metadata` with anything useful for the knowledge graph; `render()` lifts
  selected keys into frontmatter.

## Pipeline order (do not reorder)
```
registry.detect(target) → handler.extract() → enricher.enrich() → render() → writer.write()
```
`enricher.enrich()` mutates the Document in place (adds summary/tags/wikilinks) and is a
no-op when `provider=none`.
