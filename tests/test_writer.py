import pytest

from any2md.models import Document
from any2md.writer import slugify, write


@pytest.mark.parametrize(
    "title,expected",
    [
        ("How to Build X", "how-to-build-x"),
        ("Hello, World!! Test", "hello-world-test"),
        ("Café Münü", "cafe-munu"),
        ("   spaced   out   ", "spaced-out"),
        ("***", "untitled"),
    ],
)
def test_slugify(title, expected):
    assert slugify(title) == expected


def _doc(title="My Report") -> Document:
    return Document(
        title=title,
        source_url=None,
        source_type="pdf",
        upload_date=None,
        extraction_date="2026-05-28",
        body_markdown="text",
        metadata={},
    )


def test_write_creates_file_and_returns_path(tmp_path):
    out = tmp_path / "vault"
    path = write(_doc(), out)
    assert path == out / "my-report.md"
    assert path.exists()
    assert path.read_text().startswith("---\n")


def test_write_collision_appends_suffix(tmp_path):
    out = tmp_path / "vault"
    p1 = write(_doc(), out)
    p2 = write(_doc(), out)
    p3 = write(_doc(), out)
    assert p1.name == "my-report.md"
    assert p2.name == "my-report-2.md"
    assert p3.name == "my-report-3.md"
