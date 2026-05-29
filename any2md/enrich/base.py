"""Summarizer contract: produce knowledge-graph metadata from text. No APIs, no keys."""

from abc import ABC, abstractmethod


class Summarizer(ABC):
    @abstractmethod
    def summarize(self, title: str, body: str, *, ratio: float = 0.2) -> dict:
        """Distill to ~ratio of the source. Return
        {"tldr": str, "key_points": list[str], "tags": list[str], "concepts": list[str]}."""
