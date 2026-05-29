"""ETA tests — per-source heuristic that learns from recorded durations."""

from any2md import eta
from any2md.handlers.web import WebHandler
from any2md.handlers.youtube import YouTubeHandler


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_STATS", str(tmp_path / "stats.json"))


def test_classify_source_type(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert eta.classify("https://www.youtube.com/watch?v=abc") == "youtube"
    assert eta.classify("https://arxiv.org/abs/1706.03762") == "arxiv"
    assert eta.classify("https://some-blog.com/post") == "web"


def test_estimate_uses_heuristic_when_no_history(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    # youtube heuristic must be larger than a local file (caption fetch is slow)
    assert eta.estimate("youtube") > eta.estimate("file")


def test_record_then_estimate_blends_toward_observed(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    base = eta.estimate("web")
    for _ in range(5):
        eta.record("web", 30.0)  # consistently slow
    learned = eta.estimate("web")
    assert learned > base  # estimate moved toward the observed 30s


def test_unknown_source_has_a_positive_default(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert eta.estimate("nonexistent") > 0


def test_handlers_expose_source_type():
    assert YouTubeHandler.source_type == "youtube"
    assert WebHandler.source_type == "web"
