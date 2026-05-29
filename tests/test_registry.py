"""Registry routing tests — URL → correct handler, no network."""

import pytest

from any2md.handlers.github import GitHubHandler
from any2md.handlers.reddit import RedditHandler
from any2md.handlers.web import WebHandler
from any2md.handlers.youtube import YouTubeHandler
from any2md.registry import detect


def test_youtube_url_routes_to_youtube():
    assert isinstance(detect("https://www.youtube.com/watch?v=abc"), YouTubeHandler)


def test_youtu_be_routes_to_youtube():
    assert isinstance(detect("https://youtu.be/abc"), YouTubeHandler)


def test_reddit_url_routes_to_reddit():
    assert isinstance(detect("https://www.reddit.com/r/Python/comments/abc/title/"), RedditHandler)


def test_github_url_routes_to_github():
    assert isinstance(detect("https://github.com/karpathy/nanoGPT"), GitHubHandler)


def test_hackernews_url_routes():
    from any2md.handlers.hackernews import HackerNewsHandler

    assert isinstance(detect("https://news.ycombinator.com/item?id=1"), HackerNewsHandler)


def test_arxiv_url_routes():
    from any2md.handlers.arxiv import ArxivHandler

    assert isinstance(detect("https://arxiv.org/abs/1706.03762"), ArxivHandler)


def test_wikipedia_url_routes():
    from any2md.handlers.wikipedia import WikipediaHandler

    assert isinstance(detect("https://en.wikipedia.org/wiki/Transformer"), WikipediaHandler)


def test_stackoverflow_url_routes():
    from any2md.handlers.stackoverflow import StackOverflowHandler

    assert isinstance(
        detect("https://stackoverflow.com/questions/11227809/x"), StackOverflowHandler
    )


def test_twitter_url_routes():
    from any2md.handlers.twitter import TwitterHandler

    assert isinstance(detect("https://x.com/jack/status/20"), TwitterHandler)


def test_article_url_routes_to_web():
    assert isinstance(detect("https://example.com/some-article"), WebHandler)


def test_unknown_target_raises():
    with pytest.raises(ValueError):
        detect("ftp://example.com/file")
