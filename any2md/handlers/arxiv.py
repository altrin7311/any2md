"""arXiv handler — public export API (Atom), keyless. Title, authors, abstract."""

import re
import xml.etree.ElementTree as ET
from datetime import date

import httpx

from any2md.handlers.base import Handler
from any2md.models import Document

_ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+)")
_API = "https://export.arxiv.org/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"


def _fetch_atom(arxiv_id: str) -> str:
    """Fetch the arXiv Atom record — isolated for mocking."""
    resp = httpx.get(_API, params={"id_list": arxiv_id}, follow_redirects=True, timeout=15)
    resp.raise_for_status()
    return resp.text


class ArxivHandler(Handler):
    def matches(self, target: str) -> bool:
        return bool(_ARXIV_RE.search(target))

    def extract(self, target: str) -> Document:
        arxiv_id = _ARXIV_RE.search(target).group(1)
        root = ET.fromstring(_fetch_atom(arxiv_id))
        entry = root.find(f"{_ATOM}entry")
        if entry is None:
            raise ValueError(f"no arXiv record for {arxiv_id}")

        title = " ".join((entry.findtext(f"{_ATOM}title") or "").split())
        abstract = (entry.findtext(f"{_ATOM}summary") or "").strip()
        published = entry.findtext(f"{_ATOM}published")
        upload_date = published[:10] if published else None
        authors = [
            (a.findtext(f"{_ATOM}name") or "").strip() for a in entry.findall(f"{_ATOM}author")
        ]
        categories = [c.get("term") for c in entry.findall(f"{_ATOM}category") if c.get("term")]
        pdf_url = ""
        for link in entry.findall(f"{_ATOM}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")

        body = abstract
        if pdf_url:
            body += f"\n\nPDF: {pdf_url}"

        return Document(
            title=title,
            source_url=target,
            source_type="arxiv",
            upload_date=upload_date,
            extraction_date=date.today().isoformat(),
            body_markdown=body,
            metadata={
                k: v
                for k, v in {
                    "authors": authors,
                    "categories": categories,
                    "arxiv_id": arxiv_id,
                }.items()
                if v
            },
        )
