"""Web handler — trafilatura readability extraction. Catch-all for any http(s) URL."""

from datetime import date
from urllib.parse import urlparse

from any2md.handlers.base import Handler
from any2md.models import Document


def _fetch_and_extract(url: str) -> dict:
    """Fetch and extract article content — isolated for mocking in tests."""
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return {}
    metadata = trafilatura.extract_metadata(downloaded)
    text = trafilatura.extract(downloaded) or ""
    return {
        "text": text,
        "title": getattr(metadata, "title", None) if metadata else None,
        "author": getattr(metadata, "author", None) if metadata else None,
        "date": getattr(metadata, "date", None) if metadata else None,
        "sitename": getattr(metadata, "sitename", None) if metadata else None,
    }


class WebHandler(Handler):
    def matches(self, target: str) -> bool:
        return target.startswith("http://") or target.startswith("https://")

    def extract(self, target: str) -> Document:
        result = _fetch_and_extract(target)
        site = urlparse(target).netloc

        title = result.get("title") or site or "Web Article"
        body = result.get("text") or ""
        author = result.get("author") or ""
        pub_date = result.get("date") or ""
        sitename = result.get("sitename") or site

        return Document(
            title=title,
            source_url=target,
            source_type="web",
            upload_date=pub_date or None,
            extraction_date=date.today().isoformat(),
            body_markdown=body,
            metadata={k: v for k, v in {"site": sitename, "author": author}.items() if v},
        )
