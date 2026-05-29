"""Twitter/X handler — keyless syndication CDN (cdn.syndication.twimg.com).

X blocks unauthenticated API access, but the public embed/syndication endpoint still
serves single tweets with a derived token. Best-effort: single tweet, not full threads.
"""

import math
import re
from datetime import date

import httpx

from any2md.handlers.base import Handler
from any2md.models import Document

_TWEET_RE = re.compile(r"(?:twitter|x)\.com/([^/]+)/status/(\d+)")
_SYNDICATION = "https://cdn.syndication.twimg.com/tweet-result"
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)


def _syndication_token(tweet_id: str) -> str:
    """Reproduce the token the embed widget derives from the tweet id."""
    return hex(int((int(tweet_id) / 1e15) * math.pi * 1e6))[2:]


def _fetch_tweet(tweet_id: str) -> dict:
    """Fetch the syndication tweet record — isolated for mocking."""
    params = {"id": tweet_id, "lang": "en", "token": _syndication_token(tweet_id)}
    resp = httpx.get(_SYNDICATION, params=params, headers={"User-Agent": _UA}, timeout=15)
    resp.raise_for_status()
    return resp.json()


class TwitterHandler(Handler):
    source_type = "twitter"

    def matches(self, target: str) -> bool:
        return bool(_TWEET_RE.search(target))

    def extract(self, target: str) -> Document:
        tweet_id = _TWEET_RE.search(target).group(2)
        data = _fetch_tweet(tweet_id)
        if not data or not data.get("text"):
            raise ValueError(f"no tweet data for {tweet_id}")

        user = data.get("user", {})
        author = user.get("name", "")
        handle = user.get("screen_name", "")
        text = data.get("text", "")
        created = data.get("created_at", "")
        upload_date = created[:10] if created else None

        title = f"{author} (@{handle}): {text[:60]}" if handle else text[:80]

        return Document(
            title=title,
            source_url=target,
            source_type="twitter",
            upload_date=upload_date,
            extraction_date=date.today().isoformat(),
            body_markdown=text,
            metadata={
                k: v
                for k, v in {
                    "author": author,
                    "handle": handle,
                    "likes": data.get("favorite_count", 0),
                }.items()
                if v
            },
        )
