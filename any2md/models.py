"""The internal normalized document every handler produces and the renderer consumes."""

from dataclasses import dataclass, field


@dataclass
class Document:
    title: str
    source_url: str | None  # None for local files
    source_type: str  # youtube|reddit|github|web|pdf|docx|...
    upload_date: str | None  # publish/upload date (ISO) if the source has one
    extraction_date: str  # ISO date, always present
    body_markdown: str  # extracted content
    metadata: dict  # type-specific extras: channel, stars, subreddit, author...
    # filled by the enricher (later phase); empty until then:
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
