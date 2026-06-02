"""ensure_ready / _ensure_model — subprocess, httpx, and which() all mocked (no real ollama)."""

import any2md.enrich.ollama as ollama


def test_not_installed_returns_extractive(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: None)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "extractive"


def test_server_up_and_model_present_returns_ollama(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: ["llama3.2:latest"])
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "ollama"


def test_server_down_then_started(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    states = iter([False, True])  # down on first probe, up after spawn
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: next(states))
    spawned = {}
    monkeypatch.setattr(ollama, "_start_server", lambda: spawned.setdefault("did", True))
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: ["llama3.2"])
    monkeypatch.setattr(ollama.time, "sleep", lambda s: None)
    provider, note = ollama.ensure_ready(interactive=False)
    assert spawned.get("did") is True
    assert provider == "ollama"


def test_server_never_comes_up_degrades(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: False)
    monkeypatch.setattr(ollama, "_start_server", lambda: None)
    monkeypatch.setattr(ollama.time, "sleep", lambda s: None)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "extractive"
    assert "ollama" in note.lower()


def test_uses_existing_model_when_default_missing(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: ["mistral:latest"])
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "ollama"
    assert ollama.os.environ.get("OLLAMA_MODEL") == "mistral:latest"


def test_non_interactive_no_model_does_not_pull(monkeypatch, tmp_path):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: [])
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    pulled = {}
    monkeypatch.setattr(ollama, "_pull_model", lambda m: pulled.setdefault("did", True) or True)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "extractive"
    assert "did" not in pulled  # never pulls without consent
    assert "ollama pull" in note


def test_interactive_consent_yes_pulls_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: [])
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    monkeypatch.setattr(ollama, "_pull_model", lambda m: True)
    provider, note = ollama.ensure_ready(interactive=True)
    assert provider == "ollama"
    from any2md import config

    assert config.get("ollama_autopull") is True  # consent remembered
