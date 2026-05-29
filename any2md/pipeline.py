"""Orchestrates one conversion: detect → extract → enrich → render → write."""

from collections.abc import Callable
from pathlib import Path

from any2md import registry, writer
from any2md.enrich.enricher import enrich
from any2md.enrich.providers import get_summarizer


def convert(
    target: str,
    output_dir: str | Path,
    provider: str = "extractive",
    on_event: Callable[[str], None] | None = None,
) -> Path:
    def emit(stage: str) -> None:
        if on_event:
            on_event(stage)

    handler = registry.detect(target)
    emit("extracting")
    doc = handler.extract(target)
    emit("enriching")
    enrich(doc, get_summarizer(provider))
    emit("writing")
    return writer.write(doc, output_dir)
