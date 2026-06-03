"""Reddit handler tests — httpx mocked via _fetch_json / _fetch_rss."""

import json
from pathlib import Path
from unittest.mock import patch

import httpx

from any2md.handlers.reddit import RedditHandler

_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "reddit_post.json").read_text())
_RSS = (Path(__file__).parent / "fixtures" / "reddit_thread.rss").read_text()


def test_reddit_matches_thread_url():
    assert RedditHandler().matches(
        "https://www.reddit.com/r/MachineLearning/comments/abc123/title/"
    )


def test_reddit_does_not_match_subreddit_root():
    assert not RedditHandler().matches("https://www.reddit.com/r/MachineLearning/")


def test_reddit_does_not_match_other_url():
    assert not RedditHandler().matches("https://news.ycombinator.com/item?id=123")


def test_reddit_extract_document_fields():
    with patch("any2md.handlers.reddit._fetch_json", return_value=_FIXTURE):
        doc = RedditHandler().extract("https://www.reddit.com/r/MachineLearning/comments/abc123/")

    assert doc.title == "What is Retrieval Augmented Generation?"
    assert doc.source_type == "reddit"
    assert doc.metadata["subreddit"] == "MachineLearning"
    assert doc.metadata["author"] == "ml_enthusiast"
    assert doc.metadata["score"] == 250
    assert doc.upload_date == "2024-05-28"


def test_reddit_extract_includes_selftext():
    with patch("any2md.handlers.reddit._fetch_json", return_value=_FIXTURE):
        doc = RedditHandler().extract("https://www.reddit.com/r/MachineLearning/comments/abc123/")

    assert "RAG combines" in doc.body_markdown


def test_reddit_extract_raises_on_empty_thread():
    import pytest

    empty = [{"data": {"children": []}}, {"data": {"children": []}}]
    with patch("any2md.handlers.reddit._fetch_json", return_value=empty):
        with pytest.raises(ValueError):
            RedditHandler().extract("https://www.reddit.com/r/x/comments/abc/")


def test_reddit_extract_includes_comments():
    with patch("any2md.handlers.reddit._fetch_json", return_value=_FIXTURE):
        doc = RedditHandler().extract("https://www.reddit.com/r/MachineLearning/comments/abc123/")

    assert "commenter_one" in doc.body_markdown
    assert "commenter_two" in doc.body_markdown


def _blocked(*_a, **_k):
    req = httpx.Request("GET", "https://www.reddit.com/x.json")
    resp = httpx.Response(403, request=req)
    raise httpx.HTTPStatusError("403 Blocked", request=req, response=resp)


def test_reddit_falls_back_to_rss_when_json_blocked():
    with (
        patch("any2md.handlers.reddit._fetch_json", side_effect=_blocked),
        patch("any2md.handlers.reddit._fetch_rss", return_value=_RSS),
    ):
        doc = RedditHandler().extract(
            "https://www.reddit.com/r/learnmachinelearning/comments/1tprnqh/"
        )

    assert doc.source_type == "reddit"
    assert "50 tabs" in doc.title
    assert doc.metadata["subreddit"] == "learnmachinelearning"
    # comments from the RSS entries land in the body, HTML stripped
    assert "Organic_Scarcity_495" in doc.body_markdown
    assert "hardest part of learning ML" in doc.body_markdown
    assert "&lt;" not in doc.body_markdown  # HTML entities decoded


def test_reddit_rss_sets_upload_date_from_first_entry():
    with (
        patch("any2md.handlers.reddit._fetch_json", side_effect=_blocked),
        patch("any2md.handlers.reddit._fetch_rss", return_value=_RSS),
    ):
        doc = RedditHandler().extract(
            "https://www.reddit.com/r/learnmachinelearning/comments/1tprnqh/"
        )

    assert doc.upload_date == "2026-05-28"


def test_old_reddit_swaps_host():
    from any2md.handlers.reddit import _old_reddit

    assert (
        _old_reddit("https://www.reddit.com/r/x/comments/abc/t/")
        == "https://old.reddit.com/r/x/comments/abc/t/"
    )


def test_total_block_raises_source_unavailable(monkeypatch):
    import pytest

    import any2md.handlers.reddit as rd
    from any2md.errors import SourceUnavailable

    def boom(url):
        req = httpx.Request("GET", url)
        raise httpx.HTTPStatusError("403", request=req, response=httpx.Response(403, request=req))

    monkeypatch.setattr(rd, "_fetch_json", boom)
    monkeypatch.setattr(rd, "_fetch_rss", boom)
    with pytest.raises(SourceUnavailable):
        rd.RedditHandler().extract("https://www.reddit.com/r/x/comments/abc/title/")
