"""Pick the right handler for a target. Specialized handlers first; `web` catch-all stays last."""

from any2md.handlers.arxiv import ArxivHandler
from any2md.handlers.base import Handler
from any2md.handlers.files import FilesHandler
from any2md.handlers.github import GitHubHandler
from any2md.handlers.hackernews import HackerNewsHandler
from any2md.handlers.reddit import RedditHandler
from any2md.handlers.stackoverflow import StackOverflowHandler
from any2md.handlers.twitter import TwitterHandler
from any2md.handlers.web import WebHandler
from any2md.handlers.wikipedia import WikipediaHandler
from any2md.handlers.youtube import YouTubeHandler

_HANDLERS: list[Handler] = [
    YouTubeHandler(),
    RedditHandler(),
    GitHubHandler(),
    HackerNewsHandler(),
    ArxivHandler(),
    StackOverflowHandler(),
    WikipediaHandler(),
    TwitterHandler(),
    FilesHandler(),
    WebHandler(),  # catch-all — must be last
]


def detect(target: str) -> Handler:
    for handler in _HANDLERS:
        if handler.matches(target):
            return handler
    raise ValueError(f"no handler for target: {target!r}")
