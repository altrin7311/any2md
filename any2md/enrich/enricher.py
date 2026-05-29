"""Enrich a Document with a summary, tags, and wikilinks via a Summarizer.

Best-effort: a missing summarizer (None) or any summarizer error leaves the Document
unchanged, so extraction-only output always succeeds (see CLAUDE.md hard constraints).
"""

from any2md.enrich.base import Summarizer
from any2md.models import Document


def enrich(doc: Document, summarizer: Summarizer | None) -> Document:
    if summarizer is None:
        return doc
    try:
        data = summarizer.summarize(doc.title, doc.body_markdown)
        doc.summary = data.get("summary") or None
        doc.tags = list(data.get("tags") or [])
        doc.wikilinks = list(data.get("wikilinks") or [])
    except Exception:
        # Enrichment is best-effort; never fail the conversion over it.
        pass
    return doc
