import pytest
from typer.testing import CliRunner

from any2md import __version__
from any2md.cli import app

runner = CliRunner()


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "config.toml"))
    monkeypatch.delenv("ANY2MD_OUTPUT_DIR", raising=False)
    return tmp_path


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("convert", "config", "serve"):
        assert cmd in result.stdout


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_config_set_then_show_round_trips(tmp_config):
    set_result = runner.invoke(app, ["config", "set", "output", "/tmp/vault"])
    assert set_result.exit_code == 0
    show_result = runner.invoke(app, ["config", "show"])
    assert show_result.exit_code == 0
    assert "output_dir=/tmp/vault" in show_result.stdout


def test_convert_writes_file(tmp_config, monkeypatch):
    monkeypatch.setenv("ANY2MD_PROVIDER", "none")
    csv = tmp_config / "data.csv"
    csv.write_text("name,role\nAda,pioneer\n")
    out = tmp_config / "vault"
    result = runner.invoke(app, ["convert", str(csv), "-o", str(out)])
    assert result.exit_code == 0
    assert "wrote" in result.stdout.lower()
    assert (out / "data.md").exists()


def test_serve_invokes_uvicorn(monkeypatch):
    calls = {}

    def fake_run(app_obj, host, port):
        calls["host"], calls["port"] = host, port

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)
    result = runner.invoke(app, ["serve", "--port", "9123"])
    assert result.exit_code == 0
    assert calls["port"] == 9123


def test_no_args_launches_repl():
    # No stdin → REPL reads EOF immediately and exits cleanly. Welcome banner shows.
    result = runner.invoke(app, [], input="")
    assert result.exit_code == 0
    assert "Obsidian markdown" in result.stdout  # tagline from the themed welcome
