"""Local-file handler: wraps markitdown to convert pdf/docx/pptx/xlsx/csv/html/... to Markdown."""

from datetime import date
from pathlib import Path

from markitdown import MarkItDown

from any2md.handlers.base import Handler
from any2md.models import Document

# Extension → source_type. Keys define which files this handler claims.
_SOURCE_TYPE = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".pptx": "pptx",
    ".ppt": "pptx",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".csv": "csv",
    ".html": "html",
    ".htm": "html",
    ".epub": "epub",
    ".txt": "text",
    ".json": "json",
    ".xml": "xml",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
}


class FilesHandler(Handler):
    def __init__(self) -> None:
        self._md = MarkItDown()

    def matches(self, target: str) -> bool:
        if target.startswith(("http://", "https://")):
            return False  # that's a URL — leave it for the URL handlers
        return Path(target).suffix.lower() in _SOURCE_TYPE

    def extract(self, target: str) -> Document:
        path = Path(target)
        result = self._md.convert(target)
        return Document(
            title=result.title or path.stem,
            source_url=None,
            source_type=_SOURCE_TYPE[path.suffix.lower()],
            upload_date=None,
            extraction_date=date.today().isoformat(),
            body_markdown=result.text_content or "",
            metadata={},
        )
