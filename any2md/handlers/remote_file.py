"""Remote-file handler — download a file URL (pdf/docx/xlsx/...) and run it through markitdown.

Ordered just before the web catch-all: a direct link to a document must be converted as that
document, not scraped as an HTML page. Extension-less URLs stay the web handler's job.
"""

import os
import tempfile
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

import httpx
from markitdown import MarkItDown

from any2md.errors import SourceUnavailable
from any2md.handlers.base import Handler
from any2md.handlers.files import _SOURCE_TYPE  # reuse the extension → type map
from any2md.models import Document

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB cap — guards against accidentally huge downloads


def _url_suffix(url: str) -> str:
    """Lowercased file suffix of a URL path, with %-encoding decoded ("%20"/"(1)")."""
    return PurePosixPath(unquote(urlparse(url).path)).suffix.lower()


def _download(url: str) -> Path:
    """Stream a URL to a temp file (suffix preserved). Isolated for mocking in tests."""
    suffix = _url_suffix(url)
    with httpx.stream("GET", url, follow_redirects=True, timeout=30) as resp:
        resp.raise_for_status()
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        total = 0
        with os.fdopen(fd, "wb") as fh:
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > _MAX_BYTES:
                    raise SourceUnavailable(f"file too large (> {_MAX_BYTES // 1024 // 1024} MB)")
                fh.write(chunk)
    return Path(tmp)


class RemoteFileHandler(Handler):
    source_type = "remotefile"  # eta label; emitted Document uses the concrete type (pdf/docx/...)

    def __init__(self) -> None:
        self._md = MarkItDown()

    def matches(self, target: str) -> bool:
        if not target.startswith(("http://", "https://")):
            return False
        return _url_suffix(target) in _SOURCE_TYPE

    def extract(self, target: str) -> Document:
        try:
            tmp = _download(target)
        except SourceUnavailable:
            raise
        except httpx.HTTPError as exc:
            raise SourceUnavailable(f"could not download: {exc}") from exc

        try:
            source_type = _SOURCE_TYPE.get(tmp.suffix.lower(), "file")
            result = self._md.convert(str(tmp))
            body = result.text_content or ""
            title = result.title or PurePosixPath(unquote(urlparse(target).path)).stem or "Document"
        finally:
            tmp.unlink(missing_ok=True)

        return Document(
            title=title,
            source_url=target,
            source_type=source_type,
            upload_date=None,
            extraction_date=date.today().isoformat(),
            body_markdown=body,
            metadata={},
        )
