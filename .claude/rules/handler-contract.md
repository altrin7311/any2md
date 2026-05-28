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
    @abstractmethod
    def matches(self, target: str) -> bool: ...   # url regex OR file extension
    @abstractmethod
    def extract(self, target: str) -> Document: ...
```

Rules:
- A handler does **extraction only** — no LLM calls, no file writing. It returns a `Document`.
- `matches()` must be cheap and side-effect free (regex / suffix check).
- Registry tries handlers in priority order; **`web` is the catch-all fallback** and
  must be tried last. Specialized URL handlers (youtube/reddit/github) come first.
- Local-file handlers match by extension; URL handlers match by host/path regex.
- Populate `metadata` with anything useful for the knowledge graph; `render()` lifts
  selected keys into frontmatter.

## Pipeline order (do not reorder)
```
registry.detect(target) → handler.extract() → enricher.enrich() → render() → writer.write()
```
`enricher.enrich()` mutates the Document in place (adds summary/tags/wikilinks) and is a
no-op when `provider=none`.
