"""Render a Document to Obsidian-flavored Markdown (see .claude/rules/output-format.md)."""

from any2md.models import Document

# Type-specific metadata keys lifted into frontmatter, in this fixed order.
_META_LIFT = ("channel", "stars", "subreddit", "author", "license", "languages")

# Body section heading per source type; default "Content".
_SECTION = {
    "youtube": "Transcript",
    "github": "README",
    "reddit": "Thread",
}


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _format_meta(key: str, value: object) -> str:
    if isinstance(value, bool):
        return f"{key}: {str(value).lower()}"
    if isinstance(value, int):
        return f"{key}: {value}"
    if isinstance(value, (list, tuple)):
        return f"{key}: [{', '.join(str(v) for v in value)}]"
    return f"{key}: {_quote(str(value))}"


def _frontmatter(doc: Document) -> str:
    lines = [f"title: {_quote(doc.title)}"]
    if doc.source_url:
        lines.append(f"source_url: {_quote(doc.source_url)}")
    lines.append(f"source_type: {doc.source_type}")
    if doc.upload_date:
        lines.append(f"upload_date: {doc.upload_date}")
    lines.append(f"extraction_date: {doc.extraction_date}")
    for key in _META_LIFT:
        if key in doc.metadata:
            lines.append(_format_meta(key, doc.metadata[key]))
    lines.append(f"tags: [{', '.join(doc.tags)}]")
    return "---\n" + "\n".join(lines) + "\n---\n"


def render(doc: Document) -> str:
    blocks = [f"# {doc.title}"]
    if doc.summary:
        blocks.append(f"> **Summary:** {doc.summary}")
    if doc.wikilinks:
        links = ", ".join(f"[[{w}]]" for w in doc.wikilinks)
        blocks.append(f"Key concepts: {links}")
    section = _SECTION.get(doc.source_type, "Content")
    blocks.append(f"## {section}\n\n{doc.body_markdown}")
    body = "\n\n".join(blocks)
    return _frontmatter(doc) + "\n" + body + "\n"
