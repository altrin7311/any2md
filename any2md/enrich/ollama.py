"""Ollama summarizer — local model, free, no API key. Talks to a local Ollama server.

Requires the user to run Ollama (https://ollama.com) and pull a model. If the server is
unreachable, summarize() raises and the enricher falls back to extraction-only (best-effort).
"""

import json
import os

from any2md.enrich.base import Summarizer

_MAX_BODY_CHARS = 12000


def available(url: str | None = None) -> bool:
    """True if a local Ollama server answers quickly. Used for first-run auto-detect."""
    import httpx  # lazy

    base = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    try:
        return httpx.get(f"{base}/api/tags", timeout=1.5).is_success
    except Exception:
        return False


_PROMPT = (
    "Distill the following content into an Obsidian knowledge note. Keep only the most "
    "important ~{pct}% of the meaning — drop filler. "
    'Return ONLY a JSON object with keys: "tldr" (a short multi-sentence summary), '
    '"key_points" (list of concise high-signal points), '
    '"concepts" (list of key entity/concept names to link), '
    '"tags" (list of short lowercase topic tags).\n\n'
    "Title: {title}\nContent:\n{body}"
)


class OllamaSummarizer(Summarizer):
    def __init__(self, url: str | None = None, model: str | None = None) -> None:
        self.url = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")

    def summarize(self, title: str, body: str, *, ratio: float = 0.2) -> dict:
        import httpx  # lazy

        prompt = _PROMPT.format(pct=round(ratio * 100), title=title, body=body[:_MAX_BODY_CHARS])
        resp = httpx.post(
            f"{self.url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["response"])
        return {
            "tldr": data.get("tldr") or "",
            "key_points": list(data.get("key_points") or []),
            "tags": list(data.get("tags") or []),
            "concepts": list(data.get("concepts") or []),
        }
