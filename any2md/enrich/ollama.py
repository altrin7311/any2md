"""Ollama summarizer — local model, free, no API key. Talks to a local Ollama server.

Requires the user to run Ollama (https://ollama.com) and pull a model. If the server is
unreachable, summarize() raises and the enricher falls back to extraction-only (best-effort).
"""

import json
import os

from any2md.enrich.base import Summarizer

_MAX_BODY_CHARS = 12000

_PROMPT = (
    "Summarize the following content for an Obsidian knowledge graph. "
    'Return ONLY a JSON object with keys: "summary" (string), '
    '"tags" (list of short lowercase strings), '
    '"wikilinks" (list of key entity/concept names).\n\n'
    "Title: {title}\nContent:\n{body}"
)


class OllamaSummarizer(Summarizer):
    def __init__(self, url: str | None = None, model: str | None = None) -> None:
        self.url = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")

    def summarize(self, title: str, body: str) -> dict:
        import httpx  # lazy

        prompt = _PROMPT.format(title=title, body=body[:_MAX_BODY_CHARS])
        resp = httpx.post(
            f"{self.url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["response"])
        return {
            "summary": data.get("summary") or "",
            "tags": list(data.get("tags") or []),
            "wikilinks": list(data.get("wikilinks") or []),
        }
