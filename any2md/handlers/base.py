"""The Handler contract: one per source, extraction only (see .claude/rules/handler-contract.md)."""

from abc import ABC, abstractmethod

from any2md.models import Document


class Handler(ABC):
    # Stable source label, used for ETA classification before extract() runs.
    source_type: str = "unknown"

    @abstractmethod
    def matches(self, target: str) -> bool:
        """Cheap, side-effect-free check: does this handler claim the target?"""

    @abstractmethod
    def extract(self, target: str) -> Document:
        """Fetch/parse the target into a Document. No LLM calls, no file writing."""
