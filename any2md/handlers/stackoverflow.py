"""Stack Overflow handler — public Stack Exchange API, keyless. Question + top answers."""

import re
from datetime import UTC, date, datetime
from html import unescape

import httpx

from any2md.handlers.base import Handler
from any2md.models import Document

_SO_RE = re.compile(r"stackoverflow\.com/questions/(\d+)")
_API = "https://api.stackexchange.com/2.3"
_WITHBODY = {"site": "stackoverflow", "filter": "withbody"}
_MAX_ANSWERS = 3


def _fetch_question(question_id: int) -> dict:
    """Fetch the question (with body) — isolated for mocking."""
    resp = httpx.get(f"{_API}/questions/{question_id}", params=_WITHBODY, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fetch_answers(question_id: int) -> dict:
    """Fetch answers (with body), highest-voted first — isolated for mocking."""
    params = {**_WITHBODY, "sort": "votes", "order": "desc"}
    resp = httpx.get(f"{_API}/questions/{question_id}/answers", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _strip_html(html: str) -> str:
    text = unescape(html or "").replace("<p>", "\n\n")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class StackOverflowHandler(Handler):
    def matches(self, target: str) -> bool:
        return bool(_SO_RE.search(target))

    def extract(self, target: str) -> Document:
        question_id = int(_SO_RE.search(target).group(1))
        items = _fetch_question(question_id).get("items", [])
        if not items:
            raise ValueError(f"no Stack Overflow question {question_id}")
        q = items[0]

        creation = q.get("creation_date")
        upload_date = datetime.fromtimestamp(creation, UTC).date().isoformat() if creation else None

        body_parts = [_strip_html(q.get("body", ""))]
        answers = _fetch_answers(question_id).get("items", [])[:_MAX_ANSWERS]
        if answers:
            body_parts.append("## Answers\n")
            for a in answers:
                tag = " (accepted)" if a.get("is_accepted") else ""
                body_parts.append(
                    f"**{a.get('owner', {}).get('display_name', 'unknown')}** "
                    f"(score: {a.get('score', 0)}){tag}\n\n{_strip_html(a.get('body', ''))}\n"
                )

        return Document(
            title=q.get("title", "Stack Overflow question"),
            source_url=target,
            source_type="stackoverflow",
            upload_date=upload_date,
            extraction_date=date.today().isoformat(),
            body_markdown="\n\n".join(body_parts),
            metadata={
                k: v
                for k, v in {
                    "author": q.get("owner", {}).get("display_name", ""),
                    "score": q.get("score", 0),
                    "tags": q.get("tags", []),
                }.items()
                if v
            },
        )
