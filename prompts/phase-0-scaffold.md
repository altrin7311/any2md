# Phase 0 — Scaffold & CLI shell

## Context
First phase of Any2MD. Read `CLAUDE.md` and `.claude/rules/tech-stack.md` before starting.
No conversion logic yet — just a runnable package and CLI skeleton.

## Goal
A pip/uv-installable Python package `any2md` whose CLI runs, shows help, and persists config.

## Build
1. Project layout: `pyproject.toml` (Python 3.11+, console script `any2md = any2md.cli:app`),
   `any2md/__init__.py`, `tests/`, `.gitignore`, `README.md` (short).
   Dev deps: `pytest`, `ruff`. Configure ruff + pytest in `pyproject.toml`.
2. `any2md/config.py`: load/save `~/.any2md/config.toml` (stdlib `tomllib` read, `tomli-w`
   write). Defaults: `output_dir=~/Any2MD-out`, `provider=none`, `whisper_fallback=false`.
   Precedence: CLI flag > env > config.toml > default. **API keys are never written here.**
3. `any2md/cli.py`: Typer app with command STUBS that wire to nothing yet:
   - `convert <target> [-o FOLDER] [--batch FILE]` → prints "not implemented yet"
   - `config set <key> <value>` and `config show` → actually read/write config
   - `serve [--port]` → prints "not implemented yet"
   - no-arg invocation → prints "REPL not implemented yet" (real REPL in Phase 5)
   - `--version`, `--help` work.

## TDD
- `tests/test_config.py`: set→show round-trips through a tmp config path; precedence
  (env overrides file); keys never persisted to disk.
- `tests/test_cli.py`: Typer `CliRunner` — `--help` exits 0 and lists commands;
  `config set output /tmp/x` then `config show` reflects it.

## Done when
- `pip install -e .` (or `uv pip install -e .`) succeeds.
- `any2md --help` lists `convert`, `config`, `serve`.
- `any2md config set output /tmp/vault && any2md config show` shows `output_dir=/tmp/vault`.
- `pytest -q` green; `ruff check .` clean.

## Stop
Report the file tree and test output. Wait for manual testing before Phase 1.
