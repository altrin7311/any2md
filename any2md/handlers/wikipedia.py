"""Wikipedia handler — public REST summary API, keyless."""

import re
from datetime import date
from urllib.parse import unquote

import httpx

from any2md.handlers.base import Handler
from any2md.models import Document

_WIKI_RE = re.compile(r"https?://([a-z]+)\.wikipedia\.org/wiki/([^?#]+)")


def _fetch_summary(lang: str, title: str) -> dict:
    """Fetch the REST page summary — isolated for mocking."""
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    resp = httpx.get(url, headers={"User-Agent": "any2md/0.1"}, timeout=15)
    resp.raise_for_status()
    return resp.json()


class WikipediaHandler(Handler):
    source_type = "wikipedia"

    def matches(self, target: str) -> bool:
        return bool(_WIKI_RE.search(target))

    def extract(self, target: str) -> Document:
        m = _WIKI_RE.search(target)
        lang, raw_title = m.group(1), m.group(2)
        data = _fetch_summary(lang, raw_title)

        title = data.get("title") or unquote(raw_title).replace("_", " ")
        extract = (data.get("extract") or "").strip()
        timestamp = data.get("timestamp")
        upload_date = timestamp[:10] if timestamp else None

        return Document(
            title=title,
            source_url=target,
            source_type="wikipedia",
            upload_date=upload_date,
            extraction_date=date.today().isoformat(),
            body_markdown=extract,
            metadata={
                k: v
                for k, v in {
                    "description": data.get("description", ""),
                    "lang": lang,
                }.items()
                if v
            },
        )
