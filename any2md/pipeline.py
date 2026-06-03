"""Orchestrates one conversion: detect → extract → enrich → render → write."""

from collections.abc import Callable
from pathlib import Path

import httpx

from any2md import config, eta, registry, writer
from any2md.depth import bounds as depth_bounds
from any2md.depth import ratio as depth_ratio
from any2md.enrich.enricher import enrich_with_fallback
from any2md.errors import SourceUnavailable
from any2md.url import canonical_url

# Bodies shorter than this (after stripping) likely mean a paywalled / JS-only / empty source.
_LOW_CONTENT_CHARS = 50


def is_low_content(body: str) -> bool:
    return len(body.strip()) < _LOW_CONTENT_CHARS


def convert(
    target: str,
    output_dir: str | Path,
    provider: str = "extractive",
    depth: str | None = None,
    on_event: Callable[[str], None] | None = None,
) -> Path | None:
    """Returns the written note's path, or None when there was nothing to write (the source
    extracted to nothing — paywalled / JS-only / empty — so no junk note pollutes the vault)."""

    def emit(stage: str) -> None:
        if on_event:
            on_event(stage)

    from any2md.depth import is_raw

    level = depth or str(config.get("depth"))  # explicit > config/env/default

    handler = registry.detect(target)
    emit("extracting")
    try:
        doc = handler.extract(target)
    except SourceUnavailable as exc:
        emit("warn:skipped: " + str(exc))
        return None
    except httpx.HTTPStatusError as exc:
        emit(f"warn:skipped: source unavailable (HTTP {exc.response.status_code})")
        return None
    if doc.source_url:  # clean tracking junk so the vault link is canonical + dedup works
        doc.source_url = canonical_url(doc.source_url)
    emit("enriching")
    if not is_raw(level):
        kp_min, kp_max = depth_bounds(level)
        enrich_with_fallback(doc, provider, depth_ratio(level), kp_min, kp_max)
    emit("writing")
    # Nothing to show at all (empty body and no distillation) → skip, don't write a junk note.
    if not doc.summary and not doc.key_points and not doc.body_markdown.strip():
        for warning in doc.warnings:
            emit("warn:" + warning)
        emit("warn:extraction failed — source may be empty, paywalled, or JS-only; nothing written")
        return None
    if is_low_content(doc.body_markdown):
        doc.warnings.append(
            "extracted almost no content — source may be empty, paywalled, or JS-only"
        )
    path = writer.write(doc, output_dir)
    if doc.summary or doc.key_points:  # learn the per-level output size for the /depth hint
        eta.record_lines(level, len(path.read_text().splitlines()))
    for warning in doc.warnings:
        emit("warn:" + warning)
    return path
