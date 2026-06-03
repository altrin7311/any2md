"""GitHub handler — public REST API (unauthenticated, 60 req/hr)."""

import base64
import re
from datetime import date

import httpx

from any2md.handlers.base import Handler
from any2md.models import Document

_GITHUB_RE = re.compile(r"github\.com/([^/]+)/([^/?\s#]+)")
_API_BASE = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _fetch_repo(owner: str, repo: str) -> dict:
    resp = httpx.get(
        f"{_API_BASE}/repos/{owner}/{repo}", headers=_HEADERS, follow_redirects=True, timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def _fetch_readme(owner: str, repo: str) -> str:
    resp = httpx.get(
        f"{_API_BASE}/repos/{owner}/{repo}/readme",
        headers=_HEADERS,
        follow_redirects=True,
        timeout=15,
    )
    if resp.status_code == 404:
        return ""
    resp.raise_for_status()
    raw = resp.json().get("content", "")
    return base64.b64decode(raw).decode("utf-8", errors="replace")


def _fetch_languages(owner: str, repo: str) -> list[str]:
    resp = httpx.get(
        f"{_API_BASE}/repos/{owner}/{repo}/languages",
        headers=_HEADERS,
        follow_redirects=True,
        timeout=15,
    )
    if not resp.is_success:
        return []
    return list(resp.json().keys())


class GitHubHandler(Handler):
    source_type = "github"

    def matches(self, target: str) -> bool:
        return bool(_GITHUB_RE.search(target))

    def extract(self, target: str) -> Document:
        m = _GITHUB_RE.search(target)
        if not m:
            raise ValueError(f"not a GitHub repo URL: {target}")
        owner, repo = m.group(1), m.group(2).rstrip("/")

        repo_data = _fetch_repo(owner, repo)
        readme = _fetch_readme(owner, repo)
        languages = _fetch_languages(owner, repo)

        title = repo_data.get("full_name", f"{owner}/{repo}")
        description = repo_data.get("description") or ""
        stars = repo_data.get("stargazers_count", 0)
        topics = repo_data.get("topics", [])
        license_name = (repo_data.get("license") or {}).get("spdx_id") or ""
        created_at = (repo_data.get("created_at") or "")[:10]
        updated_at = (repo_data.get("updated_at") or "")[:10]

        return Document(
            title=title,
            source_url=target,
            source_type="github",
            upload_date=created_at or None,
            extraction_date=date.today().isoformat(),
            body_markdown=readme or description,
            metadata={
                k: v
                for k, v in {
                    "stars": stars,
                    "topics": topics,
                    "license": license_name,
                    "languages": languages,
                    "description": description,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }.items()
                if v not in (None, "", [], {})
            },
        )
