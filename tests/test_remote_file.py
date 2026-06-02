"""RemoteFileHandler — download helper mocked; markitdown runs on a real local sample."""

import httpx
import pytest

from any2md import registry
from any2md.errors import SourceUnavailable
from any2md.handlers.remote_file import RemoteFileHandler
from any2md.handlers.web import WebHandler

handler = RemoteFileHandler()

_PDF_URL = "https://cdn.prod.website-files.com/abc/The-Founders-Playbook_v3%20(1).pdf"


def test_matches_file_urls_by_extension():
    assert handler.matches(_PDF_URL)  # %20/() decode → .pdf
    assert handler.matches("https://example.com/report.docx")
    assert handler.matches("https://example.com/data.xlsx")


def test_does_not_match_plain_web_or_local():
    assert not handler.matches("https://example.com/article")
    assert not handler.matches("https://example.com/")
    assert not handler.matches("notes.pdf")  # local path, not a URL


def test_registry_routes_file_url_to_remote_handler():
    assert isinstance(registry.detect(_PDF_URL), RemoteFileHandler)


def test_registry_still_routes_plain_url_to_web():
    assert isinstance(registry.detect("https://example.com/article"), WebHandler)


def test_extract_downloads_and_converts(tmp_path, monkeypatch):
    sample = tmp_path / "downloaded.csv"
    sample.write_text("name,role\nAda,pioneer\n")
    monkeypatch.setattr(
        "any2md.handlers.remote_file._download",
        lambda url: sample,
    )
    doc = handler.extract("https://example.com/data.csv")
    assert doc.source_type == "csv"
    assert doc.source_url == "https://example.com/data.csv"
    assert "| name | role |" in doc.body_markdown


def test_extract_cleans_up_temp_file(tmp_path, monkeypatch):
    sample = tmp_path / "temp.csv"
    sample.write_text("a,b\n1,2\n")
    monkeypatch.setattr("any2md.handlers.remote_file._download", lambda url: sample)
    handler.extract("https://example.com/data.csv")
    assert not sample.exists()  # temp file removed after conversion


def test_download_failure_raises_source_unavailable(monkeypatch):
    def boom(url):
        raise httpx.ConnectError("dns")

    monkeypatch.setattr("any2md.handlers.remote_file._download", boom)
    with pytest.raises(SourceUnavailable):
        handler.extract("https://example.com/data.pdf")
