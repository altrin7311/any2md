"""Pick the right handler for a target. Specialized handlers first; `web` catch-all stays last."""

from any2md.handlers.base import Handler
from any2md.handlers.files import FilesHandler

# Priority order. URL handlers (youtube/reddit/github) and the `web` fallback land in Phase 4.
_HANDLERS: list[Handler] = [FilesHandler()]


def detect(target: str) -> Handler:
    for handler in _HANDLERS:
        if handler.matches(target):
            return handler
    raise ValueError(f"no handler for target: {target!r}")
