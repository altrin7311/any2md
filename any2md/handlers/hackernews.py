"""Hacker News handler — public Firebase API, keyless. Story + top comments."""

import re
from datetime import UTC, date, datetime
from html import unescape

import httpx

from any2md.handlers.base import Handler
from any2md.models import Document

_HN_RE = re.compile(r"news\.ycombinator\.com/item\?id=(\d+)")
_API = "https://hacker-news.firebaseio.com/v0/item"
_MAX_COMMENTS = 20


def _fetch_item(item_id: int) -> dict:
    """Fetch one HN item (story or comment) — isolated for mocking."""
    resp = httpx.get(f"{_API}/{item_id}.json", timeout=15)
    resp.raise_for_status()
    return resp.json() or {}


def _strip_html(html: str) -> str:
    text = unescape(html or "").replace("<p>", "\n\n")
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


class HackerNewsHandler(Handler):
    def matches(self, target: str) -> bool:
        return bool(_HN_RE.search(target))

    def extract(self, target: str) -> Document:
        item_id = int(_HN_RE.search(target).group(1))
        story = _fetch_item(item_id)

        title = story.get("title", "Hacker News item")
        time_unix = story.get("time")
        upload_date = (
            datetime.fromtimestamp(time_unix, UTC).date().isoformat() if time_unix else None
        )

        body_parts: list[str] = []
        if story.get("url"):
            body_parts.append(f"Link: {story['url']}")
        if story.get("text"):
            body_parts.append(_strip_html(story["text"]))

        kids = story.get("kids", [])[:_MAX_COMMENTS]
        if kids:
            body_parts.append("## Comments\n")
            for kid in kids:
                c = _fetch_item(kid)
                text = _strip_html(c.get("text", ""))
                if text:
                    body_parts.append(f"**{c.get('by', 'unknown')}**\n\n{text}\n")

        return Document(
            title=title,
            source_url=target,
            source_type="hackernews",
            upload_date=upload_date,
            extraction_date=date.today().isoformat(),
            body_markdown="\n\n".join(body_parts),
            metadata={
                k: v
                for k, v in {
                    "author": story.get("by", ""),
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                }.items()
                if v is not None
            },
        )
