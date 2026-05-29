"""Resolve a summarizer name into a Summarizer (or None for extraction-only). No APIs/keys."""

from any2md.enrich.base import Summarizer


def get_summarizer(name: str) -> Summarizer | None:
    """None = "no enrichment" (extraction-only). Never errors for the `none` case."""
    if name == "none":
        return None
    if name == "extractive":
        from any2md.enrich.extractive import ExtractiveSummarizer

        return ExtractiveSummarizer()
    if name == "ollama":
        from any2md.enrich.ollama import OllamaSummarizer

        return OllamaSummarizer()
    raise ValueError(f"unknown summarizer: {name!r} (use: none, extractive, ollama)")
