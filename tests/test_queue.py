"""Async job queue tests — fake converter, no real conversions."""

import asyncio
from pathlib import Path

from any2md.queue import JobQueue


def _fake_convert(target, output_dir, provider, on_event):
    if target == "boom":
        raise RuntimeError("kaboom")
    on_event("extracting")
    on_event("enriching")
    on_event("writing")
    return Path(output_dir) / f"{target}.md"


def _run(coro):
    return asyncio.run(coro)


async def _drain(q: JobQueue):
    await q.start()
    await q.join()
    await q.stop()


def test_queue_runs_all_jobs_to_done():
    q = JobQueue(convert_fn=_fake_convert, workers=2)
    ids = [q.submit(f"job{i}", "/tmp/out", "extractive") for i in range(5)]
    _run(_drain(q))

    for jid in ids:
        assert q.get(jid).status == "done"


def test_queue_emits_ordered_progress_events():
    q = JobQueue(convert_fn=_fake_convert, workers=1)
    jid = q.submit("alpha", "/tmp/out", "extractive")
    _run(_drain(q))

    assert q.get(jid).events == ["extracting", "enriching", "writing", "done"]


def test_queue_records_result_path():
    q = JobQueue(convert_fn=_fake_convert, workers=1)
    jid = q.submit("alpha", "/tmp/out", "extractive")
    _run(_drain(q))

    assert q.get(jid).result == Path("/tmp/out/alpha.md")


def test_queue_captures_per_job_error_without_killing_others():
    q = JobQueue(convert_fn=_fake_convert, workers=1)
    bad = q.submit("boom", "/tmp/out", "extractive")
    good = q.submit("ok", "/tmp/out", "extractive")
    _run(_drain(q))

    assert q.get(bad).status == "error"
    assert "kaboom" in q.get(bad).error
    assert q.get(good).status == "done"


def test_queue_all_lists_every_job():
    q = JobQueue(convert_fn=_fake_convert, workers=2)
    q.submit("a", "/tmp/out", "extractive")
    q.submit("b", "/tmp/out", "extractive")
    _run(_drain(q))

    assert len(q.all()) == 2
