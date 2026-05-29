from datetime import date

import openpyxl
import pytest

from any2md import registry
from any2md.handlers.files import FilesHandler

handler = FilesHandler()


@pytest.fixture
def samples(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("name,role\nAda,pioneer\n")
    html = tmp_path / "page.html"
    html.write_text(
        "<html><head><title>My Page</title></head>"
        "<body><h1>Heading</h1><p>Hello world.</p></body></html>"
    )
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["q", "sales"])
    ws.append(["Q1", 100])
    xlsx = tmp_path / "sheet.xlsx"
    wb.save(xlsx)
    return {"csv": csv, "html": html, "xlsx": xlsx}


def test_matches_local_files_not_urls(tmp_path):
    assert handler.matches("notes.pdf")
    assert handler.matches(str(tmp_path / "a.csv"))
    assert not handler.matches("https://example.com/page.html")
    assert not handler.matches("https://youtube.com/watch?v=x")


def test_extract_csv_falls_back_to_filename_title(samples):
    doc = handler.extract(str(samples["csv"]))
    assert doc.source_type == "csv"
    assert doc.source_url is None
    assert doc.title == "data"  # markitdown gives no title for csv → filename stem
    assert "| name | role |" in doc.body_markdown
    assert doc.extraction_date == date.today().isoformat()


def test_extract_html_uses_document_title(samples):
    doc = handler.extract(str(samples["html"]))
    assert doc.source_type == "html"
    assert doc.title == "My Page"
    assert "Heading" in doc.body_markdown


def test_extract_xlsx_binary_format(samples):
    doc = handler.extract(str(samples["xlsx"]))
    assert doc.source_type == "xlsx"
    assert "sales" in doc.body_markdown


def test_registry_routes_local_file_to_files_handler(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("a,b\n1,2\n")
    assert isinstance(registry.detect(str(csv)), FilesHandler)


def test_registry_raises_when_no_handler_matches():
    with pytest.raises(ValueError):
        registry.detect("ftp://example.com/file")  # ftp not handled by any handler


class _FakeResult:
    def __init__(self, title="", text=""):
        self.title = title
        self.text_content = text


def test_image_without_tesseract_warns_and_degrades(tmp_path, monkeypatch):
    img = tmp_path / "screenshot.png"
    img.write_bytes(b"\x89PNG\r\n")  # not a real image; convert is mocked anyway
    monkeypatch.setattr("any2md.handlers.files.shutil.which", lambda name: None)
    h = FilesHandler()
    monkeypatch.setattr(
        h._md, "convert", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no ocr"))
    )

    doc = h.extract(str(img))  # must NOT raise

    assert doc.source_type == "image"
    assert doc.body_markdown == ""
    assert any("tesseract" in w for w in doc.warnings)


def test_image_with_tesseract_extracts_and_no_warning(tmp_path, monkeypatch):
    img = tmp_path / "ocr.png"
    img.write_bytes(b"\x89PNG\r\n")
    monkeypatch.setattr("any2md.handlers.files.shutil.which", lambda name: "/usr/bin/tesseract")
    h = FilesHandler()
    monkeypatch.setattr(
        h._md, "convert", lambda *a, **k: _FakeResult(title="", text="recognized text")
    )

    doc = h.extract(str(img))

    assert doc.body_markdown == "recognized text"
    assert not any("tesseract" in w for w in doc.warnings)


def test_non_image_conversion_error_propagates(tmp_path, monkeypatch):
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"%PDF-1.4 broken")
    h = FilesHandler()
    monkeypatch.setattr(
        h._md, "convert", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("corrupt"))
    )

    with pytest.raises(RuntimeError):
        h.extract(str(pdf))
