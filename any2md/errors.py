"""Typed errors any handler can raise to signal a graceful outcome to the pipeline."""


class SourceUnavailable(Exception):
    """A source could not be fetched (dead link, blocked, oversize, unsupported).

    The pipeline catches this and turns it into a clean skip with a user-facing reason,
    never a traceback. Use it instead of letting an httpx error escape a handler.
    """
