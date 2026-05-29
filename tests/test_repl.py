"""REPL command-handling tests — submissions + config mutations, no real conversions."""

from pathlib import Path

from any2md.queue import JobQueue
from any2md.repl import Repl


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


def test_provider_command_updates_config(tmp_path):
    r = _repl(tmp_path)
    r.handle("/provider none")
    assert r.provider == "none"


def test_batch_command_submits_each_line(tmp_path):
    links = tmp_path / "links.txt"
    links.write_text("https://a.com/1\nhttps://b.com/2\n\n")
    r = _repl(tmp_path)
    r.handle(f"/batch {links}")
    assert len(r.queue.all()) == 2


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


def test_jobs_command_reports_status(tmp_path):
    r = _repl(tmp_path)
    r.handle("https://example.com/a")
    out = r.handle("/jobs")
    assert "queued" in out or "done" in out
