from pathlib import Path

from any2md.models import Document
from any2md.render import render

FIXTURES = Path(__file__).parent / "fixtures"


def _full_doc() -> Document:
    return Document(
        title="How to Build X",
        source_url="https://youtube.com/watch?v=abc",
        source_type="youtube",
        upload_date="2026-05-01",
        extraction_date="2026-05-28",
        body_markdown="Line one.\nLine two.",  # dropped — distilled output replaces it
        metadata={"channel": "Some Channel"},
        summary="A concise note on [[Embeddings]] and retrieval.",
        key_points=["[[Vector Search]] scales to billions of vectors.", "Indexes speed lookups."],
        tags=["ai", "tutorial", "systems"],
        wikilinks=["Embeddings", "Vector Search"],
    )


def _minimal_doc() -> Document:
    return Document(
        title="My Report",
        source_url=None,
        source_type="pdf",
        upload_date=None,
        extraction_date="2026-05-28",
        body_markdown="Some extracted text.",
        metadata={},
    )


def test_render_full_matches_golden():
    expected = (FIXTURES / "golden_full.md").read_text()
    assert render(_full_doc()) == expected


def test_render_minimal_matches_golden():
    expected = (FIXTURES / "golden_minimal.md").read_text()
    assert render(_minimal_doc()) == expected


def test_render_ignores_warnings_field():
    # warnings are terminal-only diagnostics; they must never leak into the .md output.
    with_warnings = _full_doc()
    with_warnings.warnings = ["ollama unreachable — used extractive instead"]
    assert render(with_warnings) == render(_full_doc())


def test_render_skips_section_heading_when_body_starts_with_heading():
    # Reddit .rss / SO bodies provide their own "## ..." — don't stack a second heading.
    doc = _minimal_doc()
    doc.source_type = "reddit"
    doc.body_markdown = "## Comments\n\n**/u/x**\n\nhi"
    out = render(doc)
    assert "## Thread" not in out  # auto section suppressed
    assert "## Comments" in out
