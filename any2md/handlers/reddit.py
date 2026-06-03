"""Reddit handler — public, no credentials.

Prefers the rich ``.json`` endpoint (scores + nested replies). Reddit now 403-blocks many
clients, so on any HTTP error we fall back to the ``.rss`` Atom feed (post + top comments,
flat, no scores). Both are keyless. Best-effort: a working ``.md`` beats a crash.
"""

import re
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from html import unescape

import httpx

from any2md.errors import SourceUnavailable
from any2md.handlers.base import Handler
from any2md.models import Document

_REDDIT_RE = re.compile(r"reddit\.com/r/[^/]+/comments/")
_SUBREDDIT_RE = re.compile(r"reddit\.com/r/([^/]+)/")
_ATOM = "{http://www.w3.org/2005/Atom}"

# A complete-ish browser UA gets past Reddit's crude bot filter more often than a bare one.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch_json(url: str) -> list:
    """Fetch Reddit thread JSON — isolated for mocking."""
    target = url if url.endswith(".json") else url.rstrip("/") + ".json"
    resp = httpx.get(target, headers=_HEADERS, follow_redirects=True, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fetch_rss(url: str) -> str:
    """Fetch the Atom comment feed — fallback when .json is blocked. Isolated for mocking."""
    target = url.rstrip("/") + "/.rss"
    resp = httpx.get(target, headers=_HEADERS, follow_redirects=True, timeout=15)
    resp.raise_for_status()
    return resp.text


def _subreddit_from_url(url: str) -> str:
    m = _SUBREDDIT_RE.search(url)
    return m.group(1) if m else ""


def _old_reddit(url: str) -> str:
    """Swap the host to old.reddit.com — its .json is blocked less aggressively."""
    return re.sub(r"https?://(www\.)?reddit\.com", "https://old.reddit.com", url)


def _strip_html(html: str) -> str:
    text = unescape(html or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _format_comment(comment: dict, depth: int = 0) -> str:
    body = comment.get("body", "").strip()
    if not body or body in ("[deleted]", "[removed]"):
        return ""
    author = comment.get("author", "unknown")
    score = comment.get("score", 0)
    indent = "  " * depth
    lines = [f"{indent}**{author}** (score: {score})", ""]
    for line in body.splitlines():
        lines.append(f"{indent}{line}")
    lines.append("")
    replies = comment.get("replies", {})
    if isinstance(replies, dict):
        for child in replies.get("data", {}).get("children", []):
            if child.get("kind") == "t1":
                sub = _format_comment(child["data"], depth + 1)
                if sub:
                    lines.append(sub)
    return "\n".join(lines)


def _extract_json(target: str, data: list) -> Document:
    children = data[0]["data"]["children"]
    if not children:
        raise ValueError(f"no post found at {target}")
    post = children[0]["data"]

    created_utc = post.get("created_utc")
    upload_date = (
        datetime.fromtimestamp(created_utc, UTC).date().isoformat() if created_utc else None
    )

    comments = [c["data"] for c in data[1]["data"]["children"] if c.get("kind") == "t1"]
    comments.sort(key=lambda c: c.get("score", 0), reverse=True)

    body_parts: list[str] = []
    selftext = post.get("selftext", "").strip()
    if selftext:
        body_parts.append(selftext)
    if comments:
        body_parts.append("## Comments\n")
        for c in comments[:20]:
            formatted = _format_comment(c)
            if formatted:
                body_parts.append(formatted)

    return Document(
        title=post.get("title", "Untitled"),
        source_url=target,
        source_type="reddit",
        upload_date=upload_date,
        extraction_date=date.today().isoformat(),
        body_markdown="\n\n".join(body_parts),
        metadata={
            k: v
            for k, v in {
                "subreddit": post.get("subreddit", ""),
                "author": post.get("author", ""),
                "score": post.get("score", 0),
            }.items()
            if v is not None
        },
    )


def _extract_rss(target: str, xml: str) -> Document:
    root = ET.fromstring(xml)
    subreddit = _subreddit_from_url(target)

    feed_title = (root.findtext(f"{_ATOM}title") or "Untitled").strip()
    # Reddit appends " : subreddit" to the feed title — drop it for a clean note title.
    if subreddit and feed_title.endswith(f": {subreddit}"):
        feed_title = feed_title[: -len(f": {subreddit}")].strip()

    upload_date = None
    body_parts: list[str] = ["## Comments\n"]
    for entry in root.findall(f"{_ATOM}entry"):
        author = (entry.findtext(f"{_ATOM}author/{_ATOM}name") or "unknown").strip()
        published = entry.findtext(f"{_ATOM}published")
        if upload_date is None and published:
            upload_date = published[:10]
        content = _strip_html(entry.findtext(f"{_ATOM}content") or "")
        if content:
            body_parts.append(f"**{author}**\n\n{content}\n")

    return Document(
        title=feed_title,
        source_url=target,
        source_type="reddit",
        upload_date=upload_date,
        extraction_date=date.today().isoformat(),
        body_markdown="\n\n".join(body_parts),
        metadata={"subreddit": subreddit} if subreddit else {},
    )


class RedditHandler(Handler):
    source_type = "reddit"

    def matches(self, target: str) -> bool:
        return bool(_REDDIT_RE.search(target))

    def extract(self, target: str) -> Document:
        try:
            return _extract_json(target, _fetch_json(target))
        except httpx.HTTPError:
            pass
        try:  # old.reddit.com is blocked less often than www
            return _extract_json(target, _fetch_json(_old_reddit(target)))
        except httpx.HTTPError:
            pass
        try:  # last resort: the keyless Atom feed (flat, no scores)
            return _extract_rss(target, _fetch_rss(target))
        except httpx.HTTPError as exc:
            raise SourceUnavailable(f"reddit blocked this request ({exc})") from exc
