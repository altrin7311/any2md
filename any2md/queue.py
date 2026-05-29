"""Async job queue — shared engine for the REPL and `serve`.

Submit a target → job id. Workers run conversions off-thread (the pipeline is blocking),
emitting progress events: queued → extracting → enriching → writing → done | error.
One failing job never kills the queue.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# Stages a converter reports via its on_event callback, in order.
STAGES = ("extracting", "enriching", "writing")


@dataclass
class Job:
    id: str
    target: str
    output_dir: str
    provider: str
    status: str = "queued"
    events: list[str] = field(default_factory=list)
    result: Path | None = None
    error: str | None = None
    done: asyncio.Event = field(default_factory=asyncio.Event)


def _default_convert(target, output_dir, provider, on_event):
    """Real converter: the pipeline, reporting stages via on_event."""
    from any2md import pipeline

    return pipeline.convert(target, output_dir, provider, on_event=on_event)


class JobQueue:
    def __init__(self, convert_fn=None, workers: int = 2):
        self._convert = convert_fn or _default_convert
        self._n = workers
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._jobs: dict[str, Job] = {}
        self._workers: list[asyncio.Task] = []

    def submit(self, target: str, output_dir: str, provider: str) -> str:
        jid = uuid.uuid4().hex[:8]
        job = Job(id=jid, target=target, output_dir=output_dir, provider=provider)
        self._jobs[jid] = job
        self._queue.put_nowait(job)
        return jid

    async def start(self) -> None:
        if not self._workers:
            self._workers = [asyncio.create_task(self._worker()) for _ in range(self._n)]

    async def join(self) -> None:
        await self._queue.join()

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        self._workers = []

    def get(self, jid: str) -> Job:
        return self._jobs[jid]

    async def wait(self, jid: str) -> Job:
        """Await until the job reaches a terminal state (done | error)."""
        job = self._jobs[jid]
        await job.done.wait()
        return job

    def all(self) -> list[Job]:
        return list(self._jobs.values())

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._run(job)
            finally:
                self._queue.task_done()

    async def _run(self, job: Job) -> None:
        def on_event(stage: str) -> None:
            job.status = stage
            job.events.append(stage)

        try:
            job.result = await asyncio.to_thread(
                self._convert, job.target, job.output_dir, job.provider, on_event
            )
            job.status = "done"
            job.events.append("done")
        except Exception as exc:  # one bad job must not kill the queue
            job.error = str(exc)
            job.status = "error"
            job.events.append("error")
        finally:
            job.done.set()
