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
    # filled by the enricher; empty until then. summary holds the TL;DR, key_points the bullets,
    # both with [[wikilinks]] inlined. wikilinks holds the raw concept phrases (not rendered).
    summary: str | None = None
    key_points: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    # terminal-only diagnostics (missing OCR binary, ollama down, empty page);
    # never rendered into the .md — surfaced by the REPL / one-shot CLI.
    warnings: list[str] = field(default_factory=list)
