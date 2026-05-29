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


def _unique(directory: Path, slug: str) -> Path:
    path = directory / f"{slug}.md"
    n = 2
    while path.exists():
        path = directory / f"{slug}-{n}.md"
        n += 1
    return path


def _find_by_source_url(directory: Path, source_url: str) -> Path | None:
    """The existing note for this source_url, if any — so re-converting refreshes one note
    (keeping a /rename'd filename) instead of spawning -2, -3 duplicates in the vault."""
    needle = f'source_url: "{source_url}"'
    for md in directory.glob("*.md"):
        head = md.read_text()[:1000]
        if not head.startswith("---"):
            continue
        frontmatter = head.split("\n---", 1)[0]
        if needle in frontmatter:
            return md
    return None


def write(doc: Document, output_dir: str | Path) -> Path:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    existing = _find_by_source_url(out, doc.source_url) if doc.source_url else None
    path = existing or _unique(out, slugify(doc.title))
    path.write_text(render(doc))
    return path


def rename_output(path: str | Path, new_name: str) -> Path:
    """Rename an already-written .md to a new slugified name (collision-safe)."""
    path = Path(path)
    target = _unique(path.parent, slugify(new_name))
    path.rename(target)
    return target
