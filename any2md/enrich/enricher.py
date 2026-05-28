"""Document enrichment. Phase 2 stub: pass-through. Real summary/tags/wikilinks land in Phase 3."""

from any2md.models import Document


def enrich(doc: Document, provider: str = "none") -> Document:
    if provider == "none":
        return doc
    # Phase 3 wires real LLM providers here; until then, no enrichment.
    return doc
