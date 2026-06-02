import tomllib

import pytest

from any2md import config


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Point config at a temp file and clear config-related env for isolation."""
    path = tmp_path / "config.toml"
    monkeypatch.setenv("ANY2MD_CONFIG", str(path))
    for var in ("ANY2MD_OUTPUT_DIR", "ANY2MD_PROVIDER", "ANY2MD_WHISPER_FALLBACK"):
        monkeypatch.delenv(var, raising=False)
    return path


def test_set_persists_under_canonical_key(tmp_config):
    config.set_value("output", "/tmp/vault")  # "output" is an alias for "output_dir"
    assert config.get("output_dir") == "/tmp/vault"
    data = tomllib.loads(tmp_config.read_text())
    assert data["output_dir"] == "/tmp/vault"


def test_defaults_when_unset(tmp_config):
    assert config.get("output_dir") == "~/Any2MD-out"
    assert config.get("provider") == "extractive"  # free, zero-setup summaries by default
    assert config.get("whisper_fallback") is False


def test_env_overrides_file(tmp_config, monkeypatch):
    config.set_value("provider", "groq")
    assert config.get("provider") == "groq"
    monkeypatch.setenv("ANY2MD_PROVIDER", "gemini")
    assert config.get("provider") == "gemini"  # env wins over file


def test_whisper_fallback_from_env_coerces_bool(tmp_config, monkeypatch):
    monkeypatch.setenv("ANY2MD_WHISPER_FALLBACK", "true")
    assert config.get("whisper_fallback") is True


def test_effective_returns_all_known_keys(tmp_config):
    assert set(config.effective()) == {
        "output_dir",
        "provider",
        "whisper_fallback",
        "depth",
        "ollama_autopull",
    }


def test_ollama_autopull_key_is_known(tmp_config):
    assert config.get("ollama_autopull") is None  # unset → "ask"
    config.set_value("ollama_autopull", True)
    assert config.get("ollama_autopull") is True


def test_api_keys_never_written_to_disk(tmp_config, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "supersecret")
    config.set_value("provider", "groq")
    text = tmp_config.read_text()
    assert "supersecret" not in text
    assert "GROQ_API_KEY" not in text


def test_set_value_rejects_unknown_key(tmp_config):
    with pytest.raises(ValueError):
        config.set_value("groq_api_key", "supersecret")
