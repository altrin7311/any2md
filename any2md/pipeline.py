"""Orchestrates one conversion: detect → extract → enrich → render → write."""

from pathlib import Path

from any2md import registry, writer
from any2md.enrich.enricher import enrich


def convert(target: str, output_dir: str | Path, provider: str = "none") -> Path:
    handler = registry.detect(target)
    doc = handler.extract(target)
    enrich(doc, provider)
    return writer.write(doc, output_dir)
