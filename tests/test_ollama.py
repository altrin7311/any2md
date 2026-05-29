"""Ollama summarizer — mocked HTTP, no live server. Verifies the new distill contract."""

import json

import httpx

from any2md.enrich.ollama import OllamaSummarizer


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return {"response": json.dumps(self._payload)}


def test_ollama_summarize_returns_new_contract(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["prompt"] = json["prompt"]
        return _Resp(
            {"tldr": "A gist.", "key_points": ["one", "two"], "concepts": ["X"], "tags": ["t"]}
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    out = OllamaSummarizer().summarize("Title", "some body text", ratio=0.35)

    assert out == {
        "tldr": "A gist.",
        "key_points": ["one", "two"],
        "tags": ["t"],
        "concepts": ["X"],
    }
    assert "some body text" in captured["prompt"]


def test_ollama_prompt_reflects_ratio(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["prompt"] = json["prompt"]
        return _Resp({"tldr": "", "key_points": [], "concepts": [], "tags": []})

    monkeypatch.setattr(httpx, "post", fake_post)
    OllamaSummarizer().summarize("T", "b", ratio=0.10)
    low = captured["prompt"]
    OllamaSummarizer().summarize("T", "b", ratio=0.35)
    high = captured["prompt"]
    assert "10%" in low and "35%" in high  # the target proportion is conveyed to the model
