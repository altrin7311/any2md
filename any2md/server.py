"""FastAPI serve mode — same pipeline + queue over HTTP. For Docker / Railway.

Auth: when a token is configured (arg or ``ANY2MD_TOKEN`` env), every route requires
``Authorization: Bearer <token>``. Unset → open (local convenience).
"""

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from any2md import __version__, config
from any2md.queue import JobQueue


class ConvertRequest(BaseModel):
    target: str
    provider: str | None = None


def create_app(
    queue: JobQueue | None = None,
    token: str | None = None,
    output_dir: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Any2MD", version=__version__)
    q = queue or JobQueue()
    out_dir = output_dir or str(config.get("output_dir"))

    @app.get("/")
    async def root() -> dict:
        """Landing info so a browser visit to the root isn't a bare 404."""
        return {
            "service": "any2md",
            "version": __version__,
            "docs": "/docs",
            "endpoints": {
                "POST /convert": "{target, provider?} → {id}",
                "GET /jobs/{id}": "status + progress",
                "GET /jobs/{id}/download": "the rendered .md",
                "GET /health": "liveness check",
            },
        }

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    def _required_token() -> str | None:
        return token if token is not None else os.environ.get("ANY2MD_TOKEN")

    def _auth(authorization: str | None = Header(default=None)) -> None:
        expected = _required_token()
        if not expected:
            return  # open when no token configured
        if authorization != f"Bearer {expected}":
            raise HTTPException(status_code=401, detail="invalid or missing token")

    @app.post("/convert")
    async def convert(req: ConvertRequest, _: None = Depends(_auth)) -> dict:
        await q.start()  # idempotent; binds workers to the running loop
        provider = req.provider or str(config.get("provider"))
        jid = q.submit(req.target, out_dir, provider)
        return {"id": jid}

    @app.get("/jobs/{jid}")
    async def job_status(jid: str, _: None = Depends(_auth)) -> dict:
        try:
            job = q.get(jid)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown job") from None
        return {
            "id": job.id,
            "status": job.status,
            "events": job.events,
            "error": job.error,
        }

    @app.get("/jobs/{jid}/download")
    async def job_download(jid: str, _: None = Depends(_auth)) -> PlainTextResponse:
        try:
            job = q.get(jid)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown job") from None
        await q.wait(jid)
        if job.error or job.result is None:
            raise HTTPException(status_code=500, detail=job.error or "conversion failed")
        return PlainTextResponse(job.result.read_text(), media_type="text/markdown")

    return app
