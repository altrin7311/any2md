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


def test_convert_prints_warning_on_low_content(tmp_config, monkeypatch):
    monkeypatch.setenv("ANY2MD_PROVIDER", "none")
    tiny = tmp_config / "tiny.txt"
    tiny.write_text("hi")
    out = tmp_config / "vault"
    result = runner.invoke(app, ["convert", str(tiny), "-o", str(out)])
    assert result.exit_code == 0
    assert "almost no content" in result.stdout


def test_convert_skipped_extraction_prints_warning_no_wrote(tmp_config, monkeypatch):
    def skip(target, out, provider, depth=None, on_event=None):
        if on_event:
            on_event("warn:extraction failed — paywalled or JS-only; nothing written")
        return None

    monkeypatch.setattr("any2md.pipeline.convert", skip)
    result = runner.invoke(
        app, ["convert", "https://paywalled.example/x", "-o", str(tmp_config / "v")]
    )
    assert result.exit_code == 0
    assert "nothing written" in result.output
    assert "wrote" not in result.output.lower()


def test_convert_failure_is_clean_not_traceback(tmp_config, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("any2md.pipeline.convert", boom)
    result = runner.invoke(
        app, ["convert", "https://arxiv.org/abs/1706.03762", "-o", str(tmp_config)]
    )
    assert result.exit_code == 1
    assert "network down" in result.output
    assert "Traceback" not in result.output  # graceful, no stack dump


def test_convert_batch_continues_past_a_failing_item(tmp_config, monkeypatch):
    monkeypatch.setenv("ANY2MD_PROVIDER", "none")
    good = tmp_config / "ok.csv"
    good.write_text("a,b\n1,2\n")
    batch = tmp_config / "list.txt"
    batch.write_text("https://bad.example/x\n" + str(good) + "\n")
    out = tmp_config / "vault"

    import any2md.pipeline as pipeline

    real = pipeline.convert

    def maybe_boom(target, *a, **k):
        if target.startswith("http"):
            raise RuntimeError("unreachable")
        return real(target, *a, **k)

    monkeypatch.setattr("any2md.pipeline.convert", maybe_boom)
    result = runner.invoke(app, ["convert", "--batch", str(batch), "-o", str(out)])
    assert "unreachable" in result.output  # the bad item reported
    assert (out / "ok.md").exists()  # the good item still converted


def test_convert_accepts_depth_flag(tmp_config, monkeypatch):
    captured = {}

    def fake(target, out, provider, depth=None, on_event=None):
        captured["depth"] = depth
        from pathlib import Path

        p = Path(out) / "x.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("---\n---\n")
        return p

    monkeypatch.setattr("any2md.pipeline.convert", fake)
    result = runner.invoke(
        app, ["convert", "https://x", "-o", str(tmp_config / "v"), "--depth", "high"]
    )
    assert result.exit_code == 0
    assert captured["depth"] == "high"


def test_convert_accepts_provider_flag(tmp_config, monkeypatch):
    captured = {}

    def fake(target, out, provider, depth=None, on_event=None):
        captured["provider"] = provider
        from pathlib import Path

        p = Path(out) / "x.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("---\n---\n")
        return p

    monkeypatch.setattr("any2md.pipeline.convert", fake)
    result = runner.invoke(
        app, ["convert", "https://x", "-o", str(tmp_config / "v"), "--provider", "none"]
    )
    assert result.exit_code == 0
    assert captured["provider"] == "none"


def test_serve_invokes_uvicorn(monkeypatch):
    calls = {}

    def fake_run(app_obj, host, port):
        calls["host"], calls["port"] = host, port

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)
    result = runner.invoke(app, ["serve", "--port", "9123"])
    assert result.exit_code == 0
    assert calls["port"] == 9123


def test_no_args_launches_repl(tmp_config):
    # Pre-create config so first-run onboarding is skipped (hermetic: no real ~/.any2md write).
    (tmp_config / "config.toml").write_text('output_dir = "/tmp/x"\n')
    # No stdin → REPL reads EOF immediately and exits cleanly. Welcome banner shows.
    result = runner.invoke(app, [], input="")
    assert result.exit_code == 0
    assert "Obsidian markdown" in result.stdout  # tagline from the themed welcome


def test_convert_calls_ollama_ensure_ready_when_provider_ollama(tmp_path, monkeypatch):
    import any2md.enrich.ollama as ollama
    from any2md import pipeline

    called = {}

    def _fake_ready(interactive):
        called["hit"] = True
        return ("extractive", "note")

    monkeypatch.setattr(ollama, "ensure_ready", _fake_ready)
    monkeypatch.setattr(pipeline, "convert", lambda *a, **k: tmp_path / "x.md")
    (tmp_path / "x.md").write_text("# x\n")

    result = runner.invoke(
        app, ["convert", "https://x.com/a", "-o", str(tmp_path), "--provider", "ollama"]
    )
    assert result.exit_code == 0
    assert called.get("hit") is True  # autostart attempted before converting
