# Phase 6 — Serve mode + Docker + Railway

## Context
Ship it. Optional HTTP `serve` mode reusing the SAME pipeline + queue, packaged in Docker,
deployable to Railway. Read `.claude/rules/tech-stack.md` (system deps, `ANY2MD_TOKEN`).
Depends on Phase 5 (`queue.py`).

## Goal
`any2md serve` exposes the converter over HTTP; a Docker image runs it; Railway hosts it
within free/hobby limits; a shared token gates public access.

## Build
1. `any2md/server.py` (FastAPI + uvicorn):
   - `POST /convert` (json: `{target}` or multipart file) → submits to `queue`, returns job id
   - `GET /jobs/{id}` → status + progress
   - `GET /jobs/{id}/download` → the rendered `.md`
   - All routes require header `Authorization: Bearer $ANY2MD_TOKEN` when the env var is set;
     open if unset (local convenience).
   - Wire `cli.py serve --port` → `uvicorn`. On Railway, `provider=extractive` (no APIs/keys).
2. `Dockerfile`: `python:3.11-slim` base, install system deps (`ffmpeg` for yt-dlp),
   `pip install .`, `ENTRYPOINT ["any2md"]`. Default CMD documented for serve.
3. `railway.toml`: build from Dockerfile; start `any2md serve --port $PORT`. Document env
   vars (`ANY2MD_TOKEN` to gate access, `ANY2MD_PROVIDER=extractive`). No API keys exist.
4. `README.md`: usage for CLI (install, REPL, one-shot) AND deploy (docker run, Railway).

## TDD
- `tests/test_server.py`: FastAPI `TestClient` — POST /convert (mocked pipeline) returns a
  job id; GET status transitions; download returns the `.md`. Auth: 401 without token when
  `ANY2MD_TOKEN` set, 200 with correct token, open when unset.

## Done when
- `pytest -q` green; `ruff check .` clean.
- `docker build -t any2md .` succeeds; `docker run ... any2md serve` boots.
- `curl -H "Authorization: Bearer $ANY2MD_TOKEN" -d '{"target":"<url>"}' .../convert`
  returns a job id; polling + download yields a `.md`.
- Deployed to Railway: a real conversion works end-to-end through the public URL.

## Stop
Report the Railway URL + a successful end-to-end conversion. This completes the MVP (Core 6).
