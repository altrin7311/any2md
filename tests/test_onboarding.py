"""First-run onboarding + /rename + tips."""

from any2md import config, onboarding, writer
from any2md.theme import CONVERTING_TIPS, SESSION_TIPS


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "config.toml"))


def test_first_run_true_before_config_exists(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert config.is_first_run() is True


def test_apply_first_run_saves_output_and_picks_extractive(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr("any2md.onboarding.ollama.available", lambda: False)

    provider = onboarding.apply_first_run(str(tmp_path / "vault"))

    assert provider == "extractive"
    assert config.get("output_dir") == str(tmp_path / "vault")
    assert config.get("provider") == "extractive"
    assert config.is_first_run() is False  # config now exists


def test_apply_first_run_uses_ollama_when_available(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr("any2md.onboarding.ollama.available", lambda: True)

    provider = onboarding.apply_first_run(str(tmp_path / "vault"))

    assert provider == "ollama"
    assert config.get("provider") == "ollama"


def test_rename_output_changes_filename(tmp_path):
    f = tmp_path / "old-name.md"
    f.write_text("# hi\n")
    new = writer.rename_output(f, "My Better Title!")
    assert new.name == "my-better-title.md"
    assert new.exists()
    assert not f.exists()


def test_rename_output_avoids_collision(tmp_path):
    (tmp_path / "taken.md").write_text("x")
    f = tmp_path / "old.md"
    f.write_text("y")
    new = writer.rename_output(f, "taken")
    assert new.name == "taken-2.md"


def test_tip_pools_are_nonempty():
    assert len(CONVERTING_TIPS) >= 3
    assert len(SESSION_TIPS) >= 3
    assert all(isinstance(t, str) and t for t in CONVERTING_TIPS + SESSION_TIPS)
