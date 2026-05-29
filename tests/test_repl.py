"""REPL command-handling tests — submissions + config mutations, no real conversions."""

from pathlib import Path

from any2md.queue import JobQueue
from any2md.repl import Repl, _opener_cmd, display_name, tldr_peek


def test_display_name_shows_full_path_first_time():
    p = Path("/vault/notes/article.md")
    assert display_name(p, False) == str(p)


def test_display_name_shows_basename_after_first():
    p = Path("/vault/notes/article.md")
    assert display_name(p, True) == "article.md"


def _fake_convert(target, output_dir, provider, on_event):
    return Path(output_dir) / "x.md"


def _repl(tmp_path):
    q = JobQueue(convert_fn=_fake_convert, workers=1)
    return Repl(queue=q, output_dir=str(tmp_path), provider="extractive")


def test_url_line_submits_job(tmp_path):
    r = _repl(tmp_path)
    r.handle("https://example.com/article")
    assert len(r.queue.all()) == 1
    assert r.queue.all()[0].target == "https://example.com/article"


def test_strips_any2md_convert_prefix(tmp_path):
    r = _repl(tmp_path)
    r.handle('any2md convert "https://arxiv.org/abs/1706.03762"')
    assert len(r.queue.all()) == 1
    assert r.queue.all()[0].target == "https://arxiv.org/abs/1706.03762"


def test_strips_bare_convert_prefix(tmp_path):
    r = _repl(tmp_path)
    r.handle("convert https://x.com/jack/status/20")
    assert len(r.queue.all()) == 1
    assert r.queue.all()[0].target == "https://x.com/jack/status/20"


def test_strips_quotes_around_url(tmp_path):
    r = _repl(tmp_path)
    r.handle('"https://arxiv.org/abs/1706.03762"')
    assert len(r.queue.all()) == 1
    assert r.queue.all()[0].target == "https://arxiv.org/abs/1706.03762"


def test_existing_path_submits_job(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hi")
    r = _repl(tmp_path)
    r.handle(str(f))
    assert len(r.queue.all()) == 1


def test_unknown_line_does_not_submit(tmp_path):
    r = _repl(tmp_path)
    out = r.handle("not a url or path")
    assert len(r.queue.all()) == 0
    assert "?" in out or "unrecognized" in out.lower() or "not" in out.lower()


def test_output_command_updates_config(tmp_path):
    r = _repl(tmp_path)
    r.handle("/output /new/dir")
    assert r.output_dir == "/new/dir"


def test_provider_command_updates_config(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.delenv("ANY2MD_PROVIDER", raising=False)
    r = _repl(tmp_path)
    r.handle("/provider none")
    assert r.provider == "none"
    from any2md import config

    assert config.get("provider") == "none"  # persisted so conversions honor it


def test_provider_command_rejects_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    r = _repl(tmp_path)
    out = r.handle("/provider gpt4")
    assert "extractive" in out and "ollama" in out and "none" in out  # usage lists valid providers
    assert r.provider == "extractive"  # unchanged


def test_batch_command_submits_each_line(tmp_path):
    links = tmp_path / "links.txt"
    links.write_text("https://a.com/1\nhttps://b.com/2\n\n")
    r = _repl(tmp_path)
    r.handle(f"/batch {links}")
    assert len(r.queue.all()) == 2


def test_rename_command_renames_last_output(tmp_path):
    r = _repl(tmp_path)
    jid = r.queue.submit("https://x.com/a", str(tmp_path), "extractive")
    job = r.queue.get(jid)
    f = tmp_path / "original.md"
    f.write_text("# x\n")
    job.result = f  # simulate a completed conversion

    out = r.handle("/rename Cool New Name")

    assert (tmp_path / "cool-new-name.md").exists()
    assert not f.exists()
    assert "cool-new-name" in out


def test_rename_with_no_output_is_graceful(tmp_path):
    r = _repl(tmp_path)
    out = r.handle("/rename whatever")
    assert "nothing" in out.lower()


def test_depth_command_shows_current(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.delenv("ANY2MD_DEPTH", raising=False)
    r = _repl(tmp_path)
    out = r.handle("/depth")
    assert "medium" in out  # current level reported


def test_depth_command_sets_and_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.delenv("ANY2MD_DEPTH", raising=False)
    r = _repl(tmp_path)
    r.handle("/depth high")
    assert r.depth == "high"
    from any2md import config

    assert config.get("depth") == "high"  # written to config so conversions honor it


def test_depth_command_accepts_raw(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.delenv("ANY2MD_DEPTH", raising=False)
    r = _repl(tmp_path)
    r.handle("/depth raw")
    assert r.depth == "raw"


def test_depth_command_rejects_bad_level(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    r = _repl(tmp_path)
    out = r.handle("/depth ludicrous")
    assert "low" in out and "high" in out and "raw" in out  # usage hint lists valid levels
    assert r.depth != "ludicrous"


def test_quit_command_signals_exit(tmp_path):
    r = _repl(tmp_path)
    assert r.handle("/quit") is None
    assert r.running is False


def test_help_command_lists_commands(tmp_path):
    r = _repl(tmp_path)
    out = r.handle("/help")
    assert "/output" in out
    assert "/provider" in out
    assert "/batch" in out


def test_tldr_peek_extracts_summary_text():
    md = (
        "---\ntitle: x\n---\n# T\n\n"
        "> [!summary] TL;DR\n> First line of the summary.\n> Second line.\n\n"
        "## Key Points\n- a point\n"
    )
    peek = tldr_peek(md)
    assert "First line of the summary." in peek
    assert "Second line." in peek
    assert ">" not in peek  # callout markers stripped
    assert "Key Points" not in peek


def test_tldr_peek_empty_when_no_summary():
    assert tldr_peek("# T\n\n## Content\n\njust a body, no summary callout") == ""


def test_opener_cmd_per_platform():
    assert _opener_cmd("darwin") == "open"
    assert _opener_cmd("linux") == "xdg-open"
    assert _opener_cmd("win32") == "start"


def test_open_last_with_no_completed_jobs_is_graceful(tmp_path):
    r = _repl(tmp_path)
    out = r.handle("/open last")
    assert "nothing" in out.lower()


def test_open_folder_invokes_opener(tmp_path, monkeypatch):
    import subprocess

    calls = {}
    monkeypatch.setattr(subprocess, "Popen", lambda args, *a, **k: calls.setdefault("args", args))
    r = _repl(tmp_path)
    out = r.handle("/open")
    assert "opening" in out.lower()
    assert str(tmp_path) in calls["args"][1]


def test_jobs_command_reports_status(tmp_path):
    r = _repl(tmp_path)
    r.handle("https://example.com/a")
    out = r.handle("/jobs")
    assert "queued" in out or "done" in out
