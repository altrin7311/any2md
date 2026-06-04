"""Pipeline orchestration tests — warning forwarding, low-content, ollama fallback. No network."""

from pathlib import Path

import pytest

import any2md.pipeline as pipeline
from any2md.enrich.base import Summarizer
from any2md.models import Document
from any2md.pipeline import convert, is_low_content


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    # Keep config/stats reads+writes off the real ~/.any2md during pipeline tests.
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "config.toml"))
    monkeypatch.setenv("ANY2MD_STATS", str(tmp_path / "stats.json"))


def _doc(body: str, *, warnings: list[str] | None = None) -> Document:
    doc = Document(
        title="T",
        source_url="https://example.com/x",
        source_type="web",
        upload_date=None,
        extraction_date="2026-05-28",
        body_markdown=body,
        metadata={},
    )
    for w in warnings or []:
        doc.warnings.append(w)
    return doc


class _Handler:
    def __init__(self, doc: Document):
        self._doc = doc

    def extract(self, target: str) -> Document:
        return self._doc


def _collect_warns(events: list[str]) -> list[str]:
    return [e[len("warn:") :] for e in events if e.startswith("warn:")]


def test_is_low_content_true_for_empty_and_short():
    assert is_low_content("") is True
    assert is_low_content("   \n  ") is True
    assert is_low_content("a few short words") is True


def test_is_low_content_false_for_substantial_body():
    assert is_low_content("x" * 60) is False


def test_convert_forwards_handler_warnings(tmp_path, monkeypatch):
    doc = _doc("x" * 60, warnings=["install tesseract for image OCR: brew install tesseract"])
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    events: list[str] = []
    convert("img.png", tmp_path, provider="none", on_event=events.append)
    assert "install tesseract for image OCR: brew install tesseract" in _collect_warns(events)


def test_convert_warns_on_low_content_but_still_writes(tmp_path, monkeypatch):
    # short but real content (e.g. a terse tweet) → still a note, with a heads-up warning
    doc = _doc("a short note")
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    events: list[str] = []
    path = convert("https://example.com/x", tmp_path, provider="none", on_event=events.append)
    assert path is not None and path.exists()
    assert any("almost no content" in w for w in _collect_warns(events))


def test_convert_skips_genuinely_empty_extraction(tmp_path, monkeypatch):
    doc = _doc("")  # nothing extracted (paywalled / JS-only)
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    events: list[str] = []
    path = convert("https://example.com/x", tmp_path, provider="none", on_event=events.append)
    assert path is None
    assert any("nothing written" in w for w in _collect_warns(events))
    assert list(Path(tmp_path).glob("*.md")) == []  # vault stays clean


def test_convert_skip_still_surfaces_handler_warnings(tmp_path, monkeypatch):
    doc = _doc("", warnings=["install tesseract for image OCR: brew install tesseract"])
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    events: list[str] = []
    path = convert("img.png", tmp_path, provider="none", on_event=events.append)
    assert path is None
    warns = _collect_warns(events)
    assert any("tesseract" in w for w in warns)
    assert any("nothing written" in w for w in warns)


def test_convert_no_low_content_warning_for_substantial_body(tmp_path, monkeypatch):
    doc = _doc("x" * 200)
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    events: list[str] = []
    convert("https://example.com/x", tmp_path, provider="none", on_event=events.append)
    assert not any("almost no content" in w for w in _collect_warns(events))


def test_convert_canonicalizes_source_url(tmp_path, monkeypatch):
    doc = _doc("x" * 200)
    doc.source_url = "https://example.com/x?utm_source=foo&gclid=bar"
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    path = convert(doc.source_url, tmp_path, provider="none", on_event=lambda s: None)
    assert 'source_url: "https://example.com/x"' in path.read_text()


def test_convert_dedups_across_tracking_variants(tmp_path, monkeypatch):
    def handler_for(target):
        d = _doc("word " * 60)
        d.source_url = target
        return _Handler(d)

    monkeypatch.setattr(pipeline.registry, "detect", handler_for)
    p1 = convert(
        "https://example.com/a?utm_source=x", tmp_path, provider="none", on_event=lambda s: None
    )
    p2 = convert(
        "https://example.com/a?gclid=y", tmp_path, provider="none", on_event=lambda s: None
    )
    assert p1 == p2
    assert len(list(Path(tmp_path).glob("*.md"))) == 1


def test_convert_falls_back_to_extractive_when_ollama_down(tmp_path, monkeypatch):
    doc = _doc("x" * 200)
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))

    class _Boom(Summarizer):
        def summarize(self, title, body, *, ratio=0.2, kp_min=3, kp_max=20):
            raise RuntimeError("connection refused")

    class _Fake(Summarizer):
        def summarize(self, title, body, *, ratio=0.2, kp_min=3, kp_max=20):
            return {"tldr": "fallback summary", "key_points": [], "concepts": [], "tags": []}

    from any2md.enrich import enricher

    monkeypatch.setattr(
        enricher,
        "get_summarizer",
        lambda name: _Boom() if name == "ollama" else _Fake(),
    )
    events: list[str] = []
    convert("https://example.com/x", tmp_path, provider="ollama", on_event=events.append)
    assert doc.summary == "fallback summary"
    assert any("ollama summarize failed" in w for w in _collect_warns(events))


class _RatioRecorder(Summarizer):
    def __init__(self, sink):
        self.sink = sink

    def summarize(self, title, body, *, ratio=0.2, kp_min=3, kp_max=20):
        self.sink["ratio"] = ratio
        return {"tldr": "t", "key_points": [], "concepts": [], "tags": []}


def test_convert_passes_explicit_depth_ratio(tmp_path, monkeypatch):
    doc = _doc("word " * 100)
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    seen: dict = {}
    from any2md.enrich import enricher

    monkeypatch.setattr(enricher, "get_summarizer", lambda name: _RatioRecorder(seen))
    convert("u", tmp_path, provider="extractive", depth="high", on_event=lambda s: None)
    assert seen["ratio"] == 0.75


def test_convert_falls_back_to_config_depth(tmp_path, monkeypatch):
    from any2md import config

    config.set_value("depth", "low")
    doc = _doc("word " * 100)
    monkeypatch.setattr(pipeline.registry, "detect", lambda t: _Handler(doc))
    seen: dict = {}
    from any2md.enrich import enricher

    monkeypatch.setattr(enricher, "get_summarizer", lambda name: _RatioRecorder(seen))
    convert("u", tmp_path, provider="extractive", on_event=lambda s: None)
    assert seen["ratio"] == 0.10


def test_convert_skips_cleanly_on_source_unavailable(tmp_path, monkeypatch):
    from any2md import pipeline, registry
    from any2md.errors import SourceUnavailable

    class _Boom:
        def extract(self, target):
            raise SourceUnavailable("could not download: 404")

    monkeypatch.setattr(registry, "detect", lambda target: _Boom())
    events = []
    out = pipeline.convert(
        "https://example.com/x.pdf",
        str(tmp_path),
        "none",
        on_event=events.append,
    )
    assert out is None  # clean skip, no file written
    assert any(e.startswith("warn:skipped:") for e in events)


def test_convert_skips_on_http_status_error(tmp_path, monkeypatch):
    import httpx

    from any2md import pipeline, registry

    class _Boom:
        def extract(self, target):
            req = httpx.Request("GET", "https://api.github.com/repos/x/y")
            raise httpx.HTTPStatusError(
                "404", request=req, response=httpx.Response(404, request=req)
            )

    monkeypatch.setattr(registry, "detect", lambda target: _Boom())
    events = []
    out = pipeline.convert("https://github.com/x/y", str(tmp_path), "none", on_event=events.append)
    assert out is None
    assert any(e.startswith("warn:skipped") for e in events)
