"""Enrich a Document with a summary, tags, and wikilinks via a Summarizer.

Best-effort: a missing summarizer (None) or any summarizer error leaves the Document
unchanged, so extraction-only output always succeeds (see CLAUDE.md hard constraints).
"""

import re
import unicodedata

from any2md.enrich.base import Summarizer
from any2md.enrich.providers import get_summarizer
from any2md.models import Document


def normalize_tag(tag: str) -> str:
    """Coerce a tag into a valid Obsidian tag: ASCII, lowercase, non-alphanumerics → hyphen,
    collapsed and trimmed. Obsidian tags cannot contain spaces, so multiword tags (common from
    ollama) become hyphenated. Returns "" for a tag that has no usable characters."""
    ascii_tag = unicodedata.normalize("NFKD", tag).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_tag.lower()).strip("-")


def _normalize_tags(tags: list[str]) -> list[str]:
    """Normalize every tag and drop empties + duplicates, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        norm = normalize_tag(tag)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def inline_links(text: str, phrases: list[str]) -> str:
    """Wrap the first bare whole-word occurrence of each phrase with [[ ]] (Obsidian links),
    preserving the original casing and never double-wrapping one already in brackets."""
    for phrase in phrases:
        pattern = re.compile(rf"(?<!\[\[)\b{re.escape(phrase)}\b(?!\]\])", re.IGNORECASE)
        text = pattern.sub(lambda m: f"[[{m.group(0)}]]", text, count=1)
    return text


def enrich(
    doc: Document,
    summarizer: Summarizer | None,
    ratio: float = 0.2,
    kp_min: int = 3,
    kp_max: int = 20,
) -> bool:
    """Distill the doc into TL;DR + key points (with [[links]] inlined) at the given depth ratio.
    Returns True on success (or no-op None summarizer), False if the summarizer raised — so
    callers can react (see enrich_with_fallback). Best-effort: never propagates an error."""
    if summarizer is None:
        return True
    try:
        data = summarizer.summarize(
            doc.title, doc.body_markdown, ratio=ratio, kp_min=kp_min, kp_max=kp_max
        )
        concepts = list(data.get("concepts") or [])
        doc.summary = inline_links(data.get("tldr") or "", concepts) or None
        doc.key_points = [inline_links(p, concepts) for p in (data.get("key_points") or [])]
        doc.tags = _normalize_tags(data.get("tags") or [])
        doc.wikilinks = concepts
        return True
    except Exception:
        # Enrichment is best-effort; never fail the conversion over it.
        return False


def enrich_with_fallback(
    doc: Document, provider: str, ratio: float = 0.2, kp_min: int = 3, kp_max: int = 20
) -> None:
    """Enrich with the chosen provider; if ollama is unreachable, transparently fall back to
    the built-in extractive summarizer and record a terminal-only warning (no silent lie)."""
    if not enrich(doc, get_summarizer(provider), ratio, kp_min, kp_max) and provider == "ollama":
        doc.warnings.append("ollama summarize failed — used extractive instead")
        enrich(doc, get_summarizer("extractive"), ratio, kp_min, kp_max)
