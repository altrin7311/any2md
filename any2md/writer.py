"""Slugify a Document's title and write its rendered Markdown to the output folder."""

import re
import unicodedata
from pathlib import Path

from any2md.models import Document
from any2md.render import render


def slugify(title: str) -> str:
    # Transliterate to ASCII (é → e), lowercase, non-alphanumerics → hyphens, collapse, trim.
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug or "untitled"


def write(doc: Document, output_dir: str | Path) -> Path:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    slug = slugify(doc.title)

    path = out / f"{slug}.md"
    n = 2
    while path.exists():
        path = out / f"{slug}-{n}.md"
        n += 1

    path.write_text(render(doc))
    return path
