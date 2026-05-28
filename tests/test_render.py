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
        body_markdown="Line one.\nLine two.",
        metadata={"channel": "Some Channel"},
        summary="A concise summary.",
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
