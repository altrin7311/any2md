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


def _url_doc(url, title="Article", body="text") -> Document:
    return Document(
        title=title,
        source_url=url,
        source_type="web",
        upload_date=None,
        extraction_date="2026-05-28",
        body_markdown=body,
        metadata={},
    )


def test_write_same_source_url_overwrites_single_file(tmp_path):
    out = tmp_path / "vault"
    p1 = write(_url_doc("https://x.com/a", body="first version"), out)
    p2 = write(_url_doc("https://x.com/a", body="second version"), out)
    assert p1 == p2
    assert list(out.glob("*.md")) == [p1]  # not two files
    assert "second version" in p2.read_text()


def test_write_different_source_url_same_title_still_suffixes(tmp_path):
    out = tmp_path / "vault"
    p1 = write(_url_doc("https://x.com/a", title="Same Title"), out)
    p2 = write(_url_doc("https://x.com/b", title="Same Title"), out)
    assert p1.name == "same-title.md"
    assert p2.name == "same-title-2.md"


def test_write_overwrites_renamed_note_by_source_url(tmp_path):
    out = tmp_path / "vault"
    p1 = write(_url_doc("https://x.com/a", title="Original"), out)
    renamed = out / "my-custom-name.md"
    p1.rename(renamed)
    p2 = write(_url_doc("https://x.com/a", title="Original", body="updated body"), out)
    assert p2 == renamed
    assert "updated body" in renamed.read_text()


def test_write_local_files_no_url_keep_suffix(tmp_path):
    # source_url is None for local files → no dedup, plain collision suffix
    out = tmp_path / "vault"
    p1 = write(_doc(), out)
    p2 = write(_doc(), out)
    assert p1.name == "my-report.md"
    assert p2.name == "my-report-2.md"
