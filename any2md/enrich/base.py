"""Summarizer contract: produce knowledge-graph metadata from text. No APIs, no keys."""

from abc import ABC, abstractmethod


class Summarizer(ABC):
    @abstractmethod
    def summarize(self, title: str, body: str) -> dict:
        """Return {"summary": str, "tags": list[str], "wikilinks": list[str]}."""
