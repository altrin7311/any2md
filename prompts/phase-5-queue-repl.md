# Phase 5 — Async queue + interactive REPL

## Context
Make it feel like Claude Code: an interactive session with live progress and batch support.
Depends on Phases 2–4 (a working `pipeline.convert`). Read `CLAUDE.md` CLI section.

## Goal
`any2md` (no args) opens a REPL where you paste links/paths, see per-job progress, change
output/provider on the fly, and run batches — backed by an async job queue.

## Build
1. `any2md/queue.py`: an `asyncio` task queue + small worker pool. Submit a job (target +
   options) → job id; emits progress events (`queued → extracting → enriching → writing →
   done/error`). This is the SHARED engine (Phase 6 `serve` reuses it).
2. `any2md/repl.py`: interactive loop (Typer/Rich + prompt input):
   - bare line that looks like a URL or existing path → submit a convert job
   - `/output <dir>`, `/provider <name>` → update live config
   - `/batch <file>` → submit every line in the file
   - `/jobs` → show running/queued/done with status
   - `/last` → print path of the last written `.md`
   - `/help`, `/quit`
   Rich renders live progress per job.
3. Wire `cli.py` no-arg invocation → launch the REPL. Keep one-shot `convert` working.

## TDD
- `tests/test_queue.py`: submit N jobs with a fake converter → all reach `done`, progress
  events ordered, errors captured per-job (one failing job doesn't kill the queue).
- `tests/test_repl.py`: feed scripted input lines → assert correct queue submissions and
  config mutations (mock the pipeline). No real conversions.

## Done when
- `pytest -q` green; `ruff check .` clean.
- Manual: launch `any2md`, paste 2–3 links, watch progress, `/jobs` lists them, files land
  in the output folder; `/batch links.txt` processes a list.

## Stop
Show a REPL session transcript. Wait for manual testing before Phase 6.
