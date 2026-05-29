"""Tests for the post-MVP handlers: HN, arXiv, Wikipedia, Stack Overflow, Twitter/X.

All network isolated behind per-handler _fetch_* helpers and replayed from fixtures.
"""

import json
from pathlib import Path
from unittest.mock import patch

from any2md.handlers.arxiv import ArxivHandler
from any2md.handlers.hackernews import HackerNewsHandler
from any2md.handlers.stackoverflow import StackOverflowHandler
from any2md.handlers.twitter import TwitterHandler
from any2md.handlers.wikipedia import WikipediaHandler

_FIX = Path(__file__).parent / "fixtures"


# --- Hacker News -------------------------------------------------------------


def _hn_fetch():
    story = json.loads((_FIX / "hn_story.json").read_text())
    comments = json.loads((_FIX / "hn_comments.json").read_text())

    def fetch(item_id):
        if item_id == story["id"]:
            return story
        return comments[str(item_id)]

    return fetch


def test_hn_matches():
    assert HackerNewsHandler().matches("https://news.ycombinator.com/item?id=1")
    assert not HackerNewsHandler().matches("https://example.com/item?id=1")


def test_hn_extract_fields_and_comments():
    with patch("any2md.handlers.hackernews._fetch_item", side_effect=_hn_fetch()):
        doc = HackerNewsHandler().extract("https://news.ycombinator.com/item?id=1")
    assert doc.title == "Y Combinator"
    assert doc.source_type == "hackernews"
    assert doc.metadata["author"] == "pg"
    assert doc.upload_date == "2006-10-09"
    assert "alice" in doc.body_markdown
    assert "incubator" in doc.body_markdown


# --- arXiv -------------------------------------------------------------------


def test_arxiv_matches():
    assert ArxivHandler().matches("https://arxiv.org/abs/1706.03762")
    assert ArxivHandler().matches("https://arxiv.org/pdf/1706.03762")
    assert not ArxivHandler().matches("https://example.com/abs/1.2")


def test_arxiv_extract_fields():
    atom = (_FIX / "arxiv_paper.xml").read_text()
    with patch("any2md.handlers.arxiv._fetch_atom", return_value=atom):
        doc = ArxivHandler().extract("https://arxiv.org/abs/1706.03762")
    assert doc.title == "Attention Is All You Need"
    assert doc.source_type == "arxiv"
    assert doc.upload_date == "2017-06-12"
    assert "Ashish Vaswani" in doc.metadata["authors"]
    assert "cs.CL" in doc.metadata["categories"]
    assert "attention mechanisms" in doc.body_markdown


# --- Wikipedia ---------------------------------------------------------------


def test_wikipedia_matches():
    assert WikipediaHandler().matches("https://en.wikipedia.org/wiki/Transformer")
    assert WikipediaHandler().matches("https://de.wikipedia.org/wiki/Auto")
    assert not WikipediaHandler().matches("https://example.com/wiki/X")


def test_wikipedia_extract_fields():
    data = json.loads((_FIX / "wikipedia_summary.json").read_text())
    with patch("any2md.handlers.wikipedia._fetch_summary", return_value=data):
        doc = WikipediaHandler().extract(
            "https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)"
        )
    assert doc.title == "Transformer (deep learning architecture)"
    assert doc.source_type == "wikipedia"
    assert "multi-head attention" in doc.body_markdown
    assert doc.metadata["lang"] == "en"


# --- Stack Overflow ----------------------------------------------------------


def test_stackoverflow_matches():
    assert StackOverflowHandler().matches("https://stackoverflow.com/questions/11227809/title")
    assert not StackOverflowHandler().matches("https://example.com/questions/1")


def test_stackoverflow_extract_question_and_answers():
    q = json.loads((_FIX / "stackoverflow_question.json").read_text())
    a = json.loads((_FIX / "stackoverflow_answers.json").read_text())
    with (
        patch("any2md.handlers.stackoverflow._fetch_question", return_value=q),
        patch("any2md.handlers.stackoverflow._fetch_answers", return_value=a),
    ):
        doc = StackOverflowHandler().extract("https://stackoverflow.com/questions/11227809/")
    assert "sorted array" in doc.title
    assert doc.source_type == "stackoverflow"
    assert "java" in doc.metadata["tags"]
    assert "branch prediction" in doc.body_markdown.lower()
    assert "Mysticial" in doc.body_markdown  # top answer author


# --- Twitter / X -------------------------------------------------------------


def test_twitter_matches():
    assert TwitterHandler().matches("https://twitter.com/jack/status/20")
    assert TwitterHandler().matches("https://x.com/jack/status/20")
    assert not TwitterHandler().matches("https://example.com/jack/status/20")


def test_twitter_extract_fields():
    data = json.loads((_FIX / "tweet_result.json").read_text())
    with patch("any2md.handlers.twitter._fetch_tweet", return_value=data):
        doc = TwitterHandler().extract("https://twitter.com/jack/status/20")
    assert doc.source_type == "twitter"
    assert doc.body_markdown == "just setting up my twttr"
    assert doc.metadata["handle"] == "jack"
    assert doc.upload_date == "2006-03-21"
