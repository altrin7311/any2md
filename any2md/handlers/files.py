"""Local-file handler: wraps markitdown to convert pdf/docx/pptx/xlsx/csv/html/... to Markdown."""

import shutil
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
    source_type = "file"

    def __init__(self) -> None:
        self._md = MarkItDown()

    def matches(self, target: str) -> bool:
        if target.startswith(("http://", "https://")):
            return False  # that's a URL — leave it for the URL handlers
        return Path(target).suffix.lower() in _SOURCE_TYPE

    def extract(self, target: str) -> Document:
        path = Path(target)
        source_type = _SOURCE_TYPE[path.suffix.lower()]
        warnings: list[str] = []

        if source_type == "image":
            # Image OCR needs the tesseract binary, which pipx can't install. Warn instead of
            # letting a markitdown traceback escape, and degrade to an empty body on failure.
            if shutil.which("tesseract") is None:
                warnings.append("install tesseract for image OCR: brew install tesseract")
            try:
                result = self._md.convert(target)
                title = result.title or path.stem
                body = result.text_content or ""
            except Exception:
                title = path.stem
                body = ""
        else:
            result = self._md.convert(target)  # genuine failures here surface as a real error
            title = result.title or path.stem
            body = result.text_content or ""

        return Document(
            title=title,
            source_url=None,
            source_type=source_type,
            upload_date=None,
            extraction_date=date.today().isoformat(),
            body_markdown=body,
            metadata={},
            warnings=warnings,
        )
