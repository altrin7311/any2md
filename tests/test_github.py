"""GitHub handler tests — HTTP calls mocked via _fetch_* helpers."""

import base64
import json
from pathlib import Path
from unittest.mock import patch

from any2md.handlers.github import GitHubHandler

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_REPO = json.loads((_FIXTURES_DIR / "github_repo.json").read_text())
_LANGUAGES = json.loads((_FIXTURES_DIR / "github_languages.json").read_text())
_README_DECODED = base64.b64decode(
    json.loads((_FIXTURES_DIR / "github_readme.json").read_text())["content"]
).decode()


def test_github_matches_repo_url():
    assert GitHubHandler().matches("https://github.com/karpathy/nanoGPT")


def test_github_matches_url_with_path():
    assert GitHubHandler().matches("https://github.com/karpathy/nanoGPT/tree/main")


def test_github_does_not_match_other():
    assert not GitHubHandler().matches("https://gitlab.com/user/repo")


def test_github_extract_document_fields():
    with (
        patch("any2md.handlers.github._fetch_repo", return_value=_REPO),
        patch("any2md.handlers.github._fetch_readme", return_value=_README_DECODED),
        patch("any2md.handlers.github._fetch_languages", return_value=list(_LANGUAGES.keys())),
    ):
        doc = GitHubHandler().extract("https://github.com/karpathy/nanoGPT")

    assert doc.title == "karpathy/nanoGPT"
    assert doc.source_type == "github"
    assert doc.metadata["stars"] == 38000
    assert doc.metadata["license"] == "MIT"
    assert doc.upload_date == "2022-12-28"
    assert "Python" in doc.metadata["languages"]


def test_github_extract_includes_readme():
    with (
        patch("any2md.handlers.github._fetch_repo", return_value=_REPO),
        patch("any2md.handlers.github._fetch_readme", return_value=_README_DECODED),
        patch("any2md.handlers.github._fetch_languages", return_value=[]),
    ):
        doc = GitHubHandler().extract("https://github.com/karpathy/nanoGPT")

    assert "GPT" in doc.body_markdown


def test_github_extract_keeps_zero_stars():
    zero_star_repo = {**_REPO, "stargazers_count": 0}
    with (
        patch("any2md.handlers.github._fetch_repo", return_value=zero_star_repo),
        patch("any2md.handlers.github._fetch_readme", return_value=""),
        patch("any2md.handlers.github._fetch_languages", return_value=[]),
    ):
        doc = GitHubHandler().extract("https://github.com/karpathy/nanoGPT")

    assert doc.metadata["stars"] == 0


def test_github_extract_includes_topics():
    with (
        patch("any2md.handlers.github._fetch_repo", return_value=_REPO),
        patch("any2md.handlers.github._fetch_readme", return_value=""),
        patch("any2md.handlers.github._fetch_languages", return_value=[]),
    ):
        doc = GitHubHandler().extract("https://github.com/karpathy/nanoGPT")

    assert "gpt" in doc.metadata["topics"]
