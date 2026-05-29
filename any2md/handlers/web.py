"""Web handler — trafilatura readability extraction. Catch-all for any http(s) URL."""

import html as _html
import re
from datetime import date
from urllib.parse import urlparse

from any2md.handlers.base import Handler
from any2md.models import Document

# Common "Title | Site Name" separators used to strip site branding off a page title.
_TITLE_SEPARATORS = (" | ", " — ", " – ", " - ", " · ", " :: ", " • ")


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
        "html": downloaded,  # raw HTML, so we can recover <title>/<h1> if trafilatura has no title
    }


def _strip_tags(fragment: str) -> str:
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _title_from_html(html: str) -> str:
    """Recover a title from raw HTML: the <title> tag, else the first <h1>."""
    for pattern in (r"<title[^>]*>(.*?)</title>", r"<h1[^>]*>(.*?)</h1>"):
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m and _strip_tags(m.group(1)):
            return _strip_tags(m.group(1))
    return ""


def _clean_title(raw: str, sitename: str | None) -> str:
    """Strip trailing site branding ("Real Headline | Site Name" → "Real Headline").
    Only strips when the trailing chunk is the known site name, or (with no site name) is a
    short branding suffix shorter than the head."""
    title = " ".join((raw or "").split())
    if not title:
        return ""
    for sep in _TITLE_SEPARATORS:
        head, found, tail = title.rpartition(sep)
        if not found or not head.strip():
            continue
        tail_low = tail.strip().lower()
        if sitename and tail_low == sitename.strip().lower():
            return head.strip()
        if not sitename and len(tail) < len(head):
            return head.strip()
    return title


class WebHandler(Handler):
    source_type = "web"

    def matches(self, target: str) -> bool:
        return target.startswith("http://") or target.startswith("https://")

    def extract(self, target: str) -> Document:
        result = _fetch_and_extract(target)
        site = urlparse(target).netloc

        sitename = result.get("sitename") or site
        raw_title = result.get("title") or _title_from_html(result.get("html") or "")
        title = _clean_title(raw_title, sitename) or site or "Web Article"
        body = result.get("text") or ""
        author = result.get("author") or ""
        pub_date = result.get("date") or ""

        return Document(
            title=title,
            source_url=target,
            source_type="web",
            upload_date=pub_date or None,
            extraction_date=date.today().isoformat(),
            body_markdown=body,
            metadata={k: v for k, v in {"site": sitename, "author": author}.items() if v},
        )
