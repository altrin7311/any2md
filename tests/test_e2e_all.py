"""Final end-to-end suite: every Core-6 source through the full pipeline.

detect → extract → enrich → render → write. All network mocked (no live calls).
Asserts each source produces a slugified .md with correct frontmatter on disk.
"""

import base64
import json
from pathlib import Path
from unittest.mock import patch

from any2md.pipeline import convert

_FIX = Path(__file__).parent / "fixtures"


def _read(out_dir: Path) -> tuple[Path, str]:
    files = list(out_dir.glob("*.md"))
    assert len(files) == 1, f"expected one .md, got {files}"
    return files[0], files[0].read_text()


# --- local file (markitdown, offline) ---------------------------------------


def test_e2e_local_file(tmp_path):
    src = tmp_path / "notes.csv"
    src.write_text("name,role\nAda,pioneer\n")
    out = tmp_path / "vault"

    convert(str(src), out, provider="extractive")

    path, text = _read(out)
    assert path.name == "notes.md"
    assert "source_type: csv" in text
    assert "extraction_date:" in text


# --- YouTube -----------------------------------------------------------------


def test_e2e_youtube(tmp_path):
    info = {
        "title": "Transformers Explained",
        "channel": "AI Channel",
        "id": "dQw4w9WgXcQ",
        "upload_date": "20240115",
        "description": "A deep dive into the Transformer architecture and self-attention.",
        "duration": 900,
        "subtitles": {},
        "automatic_captions": {},
    }
    out = tmp_path / "vault"
    with patch("any2md.handlers.youtube._ydl_extract", return_value=info):
        convert("https://www.youtube.com/watch?v=dQw4w9WgXcQ", out, provider="extractive")

    path, text = _read(out)
    assert path.name == "transformers-explained.md"
    assert "source_type: youtube" in text
    assert 'channel: "AI Channel"' in text
    assert "upload_date: 2024-01-15" in text
    assert "source_url:" in text


# --- Reddit ------------------------------------------------------------------


def test_e2e_reddit(tmp_path):
    fixture = json.loads((_FIX / "reddit_post.json").read_text())
    out = tmp_path / "vault"
    with patch("any2md.handlers.reddit._fetch_json", return_value=fixture):
        convert(
            "https://www.reddit.com/r/MachineLearning/comments/abc123/",
            out,
            provider="extractive",
        )

    path, text = _read(out)
    assert "source_type: reddit" in text
    assert 'subreddit: "MachineLearning"' in text
    assert "commenter_one" in text  # top comment carried into body


# --- GitHub ------------------------------------------------------------------


def test_e2e_github(tmp_path):
    repo = json.loads((_FIX / "github_repo.json").read_text())
    readme = base64.b64decode(
        json.loads((_FIX / "github_readme.json").read_text())["content"]
    ).decode()
    langs = list(json.loads((_FIX / "github_languages.json").read_text()).keys())
    out = tmp_path / "vault"
    with (
        patch("any2md.handlers.github._fetch_repo", return_value=repo),
        patch("any2md.handlers.github._fetch_readme", return_value=readme),
        patch("any2md.handlers.github._fetch_languages", return_value=langs),
    ):
        convert("https://github.com/karpathy/nanoGPT", out, provider="extractive")

    path, text = _read(out)
    assert "source_type: github" in text
    assert "stars: 38000" in text
    assert 'license: "MIT"' in text


# --- Web (catch-all) ---------------------------------------------------------


def test_e2e_web(tmp_path):
    result = {
        "text": "Transformers revolutionized NLP by replacing recurrence with self-attention. "
        "The architecture scales to billions of parameters.",
        "title": "The Transformer Architecture",
        "author": "Jane Doe",
        "date": "2024-03-15",
        "sitename": "example.com",
    }
    out = tmp_path / "vault"
    with patch("any2md.handlers.web._fetch_and_extract", return_value=result):
        convert("https://example.com/transformers", out, provider="extractive")

    path, text = _read(out)
    assert path.name == "the-transformer-architecture.md"
    assert "source_type: web" in text
    assert 'author: "Jane Doe"' in text


# --- provider=none still produces extraction-only output ---------------------


def test_e2e_provider_none_no_summary(tmp_path):
    src = tmp_path / "doc.csv"
    src.write_text("a,b\n1,2\n")
    out = tmp_path / "vault"

    convert(str(src), out, provider="none")

    _, text = _read(out)
    assert "> **Summary:**" not in text
    assert "source_type: csv" in text
