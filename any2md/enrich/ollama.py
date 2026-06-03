"""Ollama summarizer — local model, free, no API key. Talks to a local Ollama server.

Requires the user to run Ollama (https://ollama.com) and pull a model. If the server is
unreachable, summarize() raises and the enricher falls back to extraction-only (best-effort).
"""

import json
import os
import shutil
import subprocess
import time

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

    def summarize(
        self, title: str, body: str, *, ratio: float = 0.2, kp_min: int = 3, kp_max: int = 20
    ) -> dict:
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


def _server_up(url: str | None = None) -> bool:
    """Alias of available(); separate name so tests can mock the readiness probe cleanly."""
    return available(url)


def _list_models(url: str | None = None) -> list[str]:
    """Names of locally-pulled Ollama models (empty on any error). Isolated for mocking."""
    import httpx

    base = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    try:
        resp = httpx.get(f"{base}/api/tags", timeout=3)
        resp.raise_for_status()
        return [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception:
        return []


def _start_server() -> None:
    """Spawn `ollama serve` detached (no window, no output). Isolated for mocking."""
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _pull_model(model: str) -> bool:
    """Run `ollama pull <model>` (streams progress to the terminal). Isolated for mocking."""
    try:
        return subprocess.run(["ollama", "pull", model]).returncode == 0
    except Exception:
        return False


def _ensure_model(interactive: bool) -> tuple[bool, str]:
    """Make sure a usable model is present. Returns (ok, note)."""
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    models = _list_models()
    if any(m == model or m.startswith(model + ":") for m in models):
        return True, ""
    if models:  # a different model is already pulled — use it rather than download another
        os.environ["OLLAMA_MODEL"] = models[0]
        return True, f"using existing model {models[0]}"

    from any2md import config

    pref = config.get("ollama_autopull")
    if pref is None and interactive:
        answer = input(f"Pull {model} (~2GB) for richer summaries? [y/N] ").strip().lower()
        pref = answer in ("y", "yes")
        config.set_value("ollama_autopull", pref)
    if pref:
        if _pull_model(model):
            return True, f"pulled {model}"
        return False, f"failed to pull {model} — using extractive this session"
    return False, f"no ollama model — run: ollama pull {model} (using extractive for now)"


def ensure_ready(interactive: bool) -> tuple[str, str]:
    """Make ollama usable hands-off. Returns (provider, note) — provider is "ollama" when ready,
    else "extractive". `note` is a short, accurate status line for the caller to print."""
    if shutil.which("ollama") is None:
        return "extractive", ""  # not installed — stay silent, use extractive
    if not _server_up():
        _start_server()
        for _ in range(15):
            if _server_up():
                break
            time.sleep(1)
        else:
            return "extractive", "couldn't start ollama — using extractive this session"
    ok, note = _ensure_model(interactive)
    return ("ollama", note) if ok else ("extractive", note)
