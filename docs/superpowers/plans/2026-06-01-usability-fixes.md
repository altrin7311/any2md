# Usability Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make any2md convert direct file URLs (e.g. a `.pdf` link), auto-start Ollama on launch, and remember the output directory across restarts.

**Architecture:** A new `RemoteFileHandler` downloads file URLs and runs them through markitdown (ordered just before the web catch-all). A new `SourceUnavailable` exception lets handlers degrade to a clean skip instead of a traceback. An `ollama.ensure_ready()` helper auto-spawns `ollama serve` and ensures a model (ask-once before a large pull). The REPL `/output` command gains the missing config-persist call.

**Tech Stack:** Python 3.11, httpx, markitdown, Typer/Rich, pytest. No new dependencies.

**Branch:** `usability-fixes` (already checked out).

---

## File Structure

- Create: `any2md/errors.py` — `SourceUnavailable` exception (shared by handlers + pipeline).
- Create: `any2md/handlers/remote_file.py` — `RemoteFileHandler` + `_download` helper.
- Create: `tests/test_remote_file.py` — remote-file handler + routing tests.
- Create: `tests/test_ollama_autostart.py` — `ensure_ready` / `_ensure_model` tests.
- Modify: `any2md/repl.py` — `/output` persists to config; startup prints the output dir.
- Modify: `any2md/registry.py` — register `RemoteFileHandler` before `WebHandler`.
- Modify: `any2md/pipeline.py` — catch `SourceUnavailable` → clean skip.
- Modify: `any2md/enrich/ollama.py` — `ensure_ready`, `_ensure_model`, server/model helpers.
- Modify: `any2md/config.py` — add `ollama_autopull` key.
- Modify: `any2md/cli.py` — call `ensure_ready` before a one-shot convert when provider is ollama.
- Modify: `tests/test_repl.py` — strengthen the `/output` test to assert persistence.

---

## Task 1: Persist `/output` (Component C)

**Files:**
- Modify: `any2md/repl.py:199-203`
- Test: `tests/test_repl.py:71-74`

- [ ] **Step 1: Replace the weak `/output` test with one that asserts persistence**

In `tests/test_repl.py`, replace the existing `test_output_command_updates_config` (lines 71-74):

```python
def test_output_command_updates_config(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.delenv("ANY2MD_OUTPUT_DIR", raising=False)
    r = _repl(tmp_path)
    r.handle("/output /new/dir")
    assert r.output_dir == "/new/dir"
    from any2md import config

    assert config.get("output_dir") == "/new/dir"  # persisted so next launch remembers it
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/pytest tests/test_repl.py::test_output_command_updates_config -v`
Expected: FAIL — `config.get("output_dir")` returns the default `~/Any2MD-out`, not `/new/dir`.

- [ ] **Step 3: Add the missing persist call**

In `any2md/repl.py`, the `/output` branch of `_command` currently reads:

```python
        if cmd == "/output":
            if not arg:
                return f"output_dir = {self.output_dir}"
            self.output_dir = _clean_dropped_path(arg)
            return f"output_dir set to {self.output_dir}"
```

Replace it with (adds the `config.set_value` call, mirroring `/provider` and `/depth`):

```python
        if cmd == "/output":
            if not arg:
                return f"output_dir = {self.output_dir}"
            from any2md import config

            self.output_dir = _clean_dropped_path(arg)
            config.set_value("output_dir", self.output_dir)
            return f"output_dir set to {self.output_dir}"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_repl.py::test_output_command_updates_config -v`
Expected: PASS

- [ ] **Step 5: Show the active output dir at startup**

In `any2md/repl.py`, in the `run` method, immediately after `print_welcome(console)` (around line 454), add:

```python
        console.print(Text(f"  output: {self.output_dir}", style="dim"))
```

(`Text` is already imported inside `run`.)

- [ ] **Step 6: Commit**

```bash
git add any2md/repl.py tests/test_repl.py
git commit -m "fix: persist /output to config so the dir is remembered; show it at startup"
```

---

## Task 2: `SourceUnavailable` + pipeline clean-skip

**Files:**
- Create: `any2md/errors.py`
- Modify: `any2md/pipeline.py:37-39`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pipeline.py`:

```python
def test_convert_skips_cleanly_on_source_unavailable(tmp_path, monkeypatch):
    from any2md import pipeline, registry
    from any2md.errors import SourceUnavailable

    class _Boom:
        def extract(self, target):
            raise SourceUnavailable("could not download: 404")

    monkeypatch.setattr(registry, "detect", lambda target: _Boom())
    events = []
    out = pipeline.convert(
        "https://example.com/x.pdf", str(tmp_path), "none",
        on_event=events.append,
    )
    assert out is None  # clean skip, no file written
    assert any(e.startswith("warn:skipped:") for e in events)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/pytest tests/test_pipeline.py::test_convert_skips_cleanly_on_source_unavailable -v`
Expected: FAIL — `ModuleNotFoundError: any2md.errors` (or the exception propagates).

- [ ] **Step 3: Create the exception module**

Create `any2md/errors.py`:

```python
"""Typed errors any handler can raise to signal a graceful outcome to the pipeline."""


class SourceUnavailable(Exception):
    """A source could not be fetched (dead link, blocked, oversize, unsupported).

    The pipeline catches this and turns it into a clean skip with a user-facing reason,
    never a traceback. Use it instead of letting an httpx error escape a handler.
    """
```

- [ ] **Step 4: Catch it in the pipeline**

In `any2md/pipeline.py`, add the import near the top (after the existing `from any2md.url import canonical_url`):

```python
from any2md.errors import SourceUnavailable
```

Then change the extract block (currently lines 37-39):

```python
    handler = registry.detect(target)
    emit("extracting")
    doc = handler.extract(target)
```

to:

```python
    handler = registry.detect(target)
    emit("extracting")
    try:
        doc = handler.extract(target)
    except SourceUnavailable as exc:
        emit("warn:skipped: " + str(exc))
        return None
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_pipeline.py::test_convert_skips_cleanly_on_source_unavailable -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add any2md/errors.py any2md/pipeline.py tests/test_pipeline.py
git commit -m "feat: SourceUnavailable exception → clean pipeline skip instead of traceback"
```

---

## Task 3: `RemoteFileHandler` (Component A)

**Files:**
- Create: `any2md/handlers/remote_file.py`
- Modify: `any2md/registry.py`
- Test: `tests/test_remote_file.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_remote_file.py`:

```python
"""RemoteFileHandler — download helper mocked; markitdown runs on a real local sample."""

from pathlib import Path

import httpx
import pytest

from any2md import registry
from any2md.errors import SourceUnavailable
from any2md.handlers.remote_file import RemoteFileHandler
from any2md.handlers.web import WebHandler

handler = RemoteFileHandler()

_PDF_URL = (
    "https://cdn.prod.website-files.com/abc/"
    "The-Founders-Playbook_v3%20(1).pdf"
)


def test_matches_file_urls_by_extension():
    assert handler.matches(_PDF_URL)  # %20/() decode → .pdf
    assert handler.matches("https://example.com/report.docx")
    assert handler.matches("https://example.com/data.xlsx")


def test_does_not_match_plain_web_or_local():
    assert not handler.matches("https://example.com/article")
    assert not handler.matches("https://example.com/")
    assert not handler.matches("notes.pdf")  # local path, not a URL


def test_registry_routes_file_url_to_remote_handler():
    assert isinstance(registry.detect(_PDF_URL), RemoteFileHandler)


def test_registry_still_routes_plain_url_to_web():
    assert isinstance(registry.detect("https://example.com/article"), WebHandler)


def test_extract_downloads_and_converts(tmp_path, monkeypatch):
    # A real CSV on disk standing in for the "downloaded" file; markitdown converts it for real.
    sample = tmp_path / "downloaded.csv"
    sample.write_text("name,role\nAda,pioneer\n")
    monkeypatch.setattr(
        "any2md.handlers.remote_file._download",
        lambda url: sample,
    )
    doc = handler.extract("https://example.com/data.csv")
    assert doc.source_type == "csv"
    assert doc.source_url == "https://example.com/data.csv"
    assert "| name | role |" in doc.body_markdown


def test_extract_cleans_up_temp_file(tmp_path, monkeypatch):
    sample = tmp_path / "temp.csv"
    sample.write_text("a,b\n1,2\n")
    monkeypatch.setattr("any2md.handlers.remote_file._download", lambda url: sample)
    handler.extract("https://example.com/data.csv")
    assert not sample.exists()  # temp file removed after conversion


def test_download_failure_raises_source_unavailable(monkeypatch):
    def boom(url):
        raise httpx.ConnectError("dns")

    monkeypatch.setattr("any2md.handlers.remote_file._download", boom)
    with pytest.raises(SourceUnavailable):
        handler.extract("https://example.com/data.pdf")
```

- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/bin/pytest tests/test_remote_file.py -v`
Expected: FAIL — `ModuleNotFoundError: any2md.handlers.remote_file`.

- [ ] **Step 3: Implement the handler**

Create `any2md/handlers/remote_file.py`:

```python
"""Remote-file handler — download a file URL (pdf/docx/xlsx/...) and run it through markitdown.

Ordered just before the web catch-all: a direct link to a document must be converted as that
document, not scraped as an HTML page. Extension-less URLs stay the web handler's job.
"""

import os
import tempfile
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

import httpx
from markitdown import MarkItDown

from any2md.errors import SourceUnavailable
from any2md.handlers.base import Handler
from any2md.handlers.files import _SOURCE_TYPE  # reuse the extension → type map
from any2md.models import Document

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB cap — guards against accidentally huge downloads


def _url_suffix(url: str) -> str:
    """Lowercased file suffix of a URL path, with %-encoding decoded ("%20"/"(1)")."""
    return PurePosixPath(unquote(urlparse(url).path)).suffix.lower()


def _download(url: str) -> Path:
    """Stream a URL to a temp file (suffix preserved). Isolated for mocking in tests."""
    suffix = _url_suffix(url)
    with httpx.stream("GET", url, follow_redirects=True, timeout=30) as resp:
        resp.raise_for_status()
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        total = 0
        with os.fdopen(fd, "wb") as fh:
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > _MAX_BYTES:
                    raise SourceUnavailable(
                        f"file too large (> {_MAX_BYTES // 1024 // 1024} MB)"
                    )
                fh.write(chunk)
    return Path(tmp)


class RemoteFileHandler(Handler):
    source_type = "remotefile"  # eta label; emitted Document uses the concrete type (pdf/docx/...)

    def __init__(self) -> None:
        self._md = MarkItDown()

    def matches(self, target: str) -> bool:
        if not target.startswith(("http://", "https://")):
            return False
        return _url_suffix(target) in _SOURCE_TYPE

    def extract(self, target: str) -> Document:
        try:
            tmp = _download(target)
        except SourceUnavailable:
            raise
        except httpx.HTTPError as exc:
            raise SourceUnavailable(f"could not download: {exc}") from exc

        try:
            source_type = _SOURCE_TYPE.get(tmp.suffix.lower(), "file")
            result = self._md.convert(str(tmp))
            body = result.text_content or ""
            title = (
                result.title
                or PurePosixPath(unquote(urlparse(target).path)).stem
                or "Document"
            )
        finally:
            tmp.unlink(missing_ok=True)

        return Document(
            title=title,
            source_url=target,
            source_type=source_type,
            upload_date=None,
            extraction_date=date.today().isoformat(),
            body_markdown=body,
            metadata={},
        )
```

- [ ] **Step 4: Register it before the web catch-all**

In `any2md/registry.py`, add the import alongside the others:

```python
from any2md.handlers.remote_file import RemoteFileHandler
```

Then in the `_HANDLERS` list, insert it between `FilesHandler()` and `WebHandler()`:

```python
    FilesHandler(),
    RemoteFileHandler(),
    WebHandler(),  # catch-all — must be last
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_remote_file.py -v`
Expected: PASS (all 6)

- [ ] **Step 6: Commit**

```bash
git add any2md/handlers/remote_file.py any2md/registry.py tests/test_remote_file.py
git commit -m "feat: RemoteFileHandler — download file URLs (pdf/docx/...) through markitdown"
```

---

## Task 4: Ollama config key

**Files:**
- Modify: `any2md/config.py:14-19`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_ollama_autopull_key_is_known(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    from any2md import config

    assert config.get("ollama_autopull") is None  # unset → "ask"
    config.set_value("ollama_autopull", True)
    assert config.get("ollama_autopull") is True
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/pytest tests/test_config.py::test_ollama_autopull_key_is_known -v`
Expected: FAIL — `ValueError: unknown config key: 'ollama_autopull'`.

- [ ] **Step 3: Add the key to DEFAULTS**

In `any2md/config.py`, extend the `DEFAULTS` dict (lines 14-19) with the new key:

```python
DEFAULTS: dict[str, object] = {
    "output_dir": "~/Any2MD-out",
    "provider": "extractive",  # free, zero-setup summaries; "ollama" or "none" also valid
    "whisper_fallback": False,
    "depth": "medium",  # summary depth: low|medium|high — fraction of source kept (see depth.py)
    "ollama_autopull": None,  # None = ask once before a large model pull; True/False remembers it
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_config.py::test_ollama_autopull_key_is_known -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add any2md/config.py tests/test_config.py
git commit -m "feat: add ollama_autopull config key (None=ask, True/False remembered)"
```

---

## Task 5: Ollama autostart helpers

**Files:**
- Modify: `any2md/enrich/ollama.py`
- Test: `tests/test_ollama_autostart.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ollama_autostart.py`:

```python
"""ensure_ready / _ensure_model — subprocess, httpx, and which() all mocked (no real ollama)."""

import any2md.enrich.ollama as ollama


def test_not_installed_returns_extractive(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: None)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "extractive"


def test_server_up_and_model_present_returns_ollama(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: ["llama3.2:latest"])
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "ollama"


def test_server_down_then_started(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    states = iter([False, True])  # down on first probe, up after spawn
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: next(states))
    spawned = {}
    monkeypatch.setattr(ollama, "_start_server", lambda: spawned.setdefault("did", True))
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: ["llama3.2"])
    monkeypatch.setattr(ollama.time, "sleep", lambda s: None)
    provider, note = ollama.ensure_ready(interactive=False)
    assert spawned.get("did") is True
    assert provider == "ollama"


def test_server_never_comes_up_degrades(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: False)
    monkeypatch.setattr(ollama, "_start_server", lambda: None)
    monkeypatch.setattr(ollama.time, "sleep", lambda s: None)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "extractive"
    assert "ollama" in note.lower()


def test_uses_existing_model_when_default_missing(monkeypatch):
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: ["mistral:latest"])
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "ollama"
    assert ollama.os.environ.get("OLLAMA_MODEL") == "mistral:latest"


def test_non_interactive_no_model_does_not_pull(monkeypatch, tmp_path):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: [])
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    pulled = {}
    monkeypatch.setattr(ollama, "_pull_model", lambda m: pulled.setdefault("did", True) or True)
    provider, note = ollama.ensure_ready(interactive=False)
    assert provider == "extractive"
    assert "did" not in pulled  # never pulls without consent
    assert "ollama pull" in note


def test_interactive_consent_yes_pulls_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/ollama")
    monkeypatch.setattr(ollama, "_server_up", lambda url=None: True)
    monkeypatch.setattr(ollama, "_list_models", lambda url=None: [])
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    monkeypatch.setattr(ollama, "_pull_model", lambda m: True)
    provider, note = ollama.ensure_ready(interactive=True)
    assert provider == "ollama"
    from any2md import config

    assert config.get("ollama_autopull") is True  # consent remembered
```

- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/bin/pytest tests/test_ollama_autostart.py -v`
Expected: FAIL — `AttributeError: module 'any2md.enrich.ollama' has no attribute 'ensure_ready'`.

- [ ] **Step 3: Implement the helpers**

In `any2md/enrich/ollama.py`, add these imports at the top (after the existing `import os`):

```python
import shutil
import subprocess
import time
```

Then append to the module (after the `available` function is fine; order does not matter):

```python
def _server_up(url: str | None = None) -> bool:
    """Alias of available(); separate name so tests can mock the readiness probe cleanly."""
    return available(url)


def _list_models(url: str | None = None) -> list[str]:
    """Names of locally-pulled Ollama models (empty on any error). Isolated for mocking."""
    import httpx

    base = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    try:
        resp = httpx.get(f"{base}/api/tags", timeout=3)
        resp.raise_for_status()
        return [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception:
        return []


def _start_server() -> None:
    """Spawn `ollama serve` detached (no window, no output). Isolated for mocking."""
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _pull_model(model: str) -> bool:
    """Run `ollama pull <model>` (streams progress to the terminal). Isolated for mocking."""
    try:
        return subprocess.run(["ollama", "pull", model]).returncode == 0
    except Exception:
        return False


def _ensure_model(interactive: bool) -> tuple[bool, str]:
    """Make sure a usable model is present. Returns (ok, note)."""
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    models = _list_models()
    if any(m == model or m.startswith(model + ":") for m in models):
        return True, ""
    if models:  # a different model is already pulled — use it rather than download another
        os.environ["OLLAMA_MODEL"] = models[0]
        return True, f"using existing model {models[0]}"

    from any2md import config

    pref = config.get("ollama_autopull")
    if pref is None and interactive:
        answer = input(f"Pull {model} (~2GB) for richer summaries? [y/N] ").strip().lower()
        pref = answer in ("y", "yes")
        config.set_value("ollama_autopull", pref)
    if pref:
        if _pull_model(model):
            return True, f"pulled {model}"
        return False, f"failed to pull {model} — using extractive this session"
    return False, f"no ollama model — run: ollama pull {model} (using extractive for now)"


def ensure_ready(interactive: bool) -> tuple[str, str]:
    """Make ollama usable hands-off. Returns (provider, note) — provider is "ollama" when ready,
    else "extractive". `note` is a short, accurate status line for the caller to print."""
    if shutil.which("ollama") is None:
        return "extractive", ""  # not installed — stay silent, use extractive
    if not _server_up():
        _start_server()
        for _ in range(15):
            if _server_up():
                break
            time.sleep(1)
        else:
            return "extractive", "couldn't start ollama — using extractive this session"
    ok, note = _ensure_model(interactive)
    return ("ollama", note) if ok else ("extractive", note)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_ollama_autostart.py -v`
Expected: PASS (all 7)

- [ ] **Step 5: Commit**

```bash
git add any2md/enrich/ollama.py tests/test_ollama_autostart.py
git commit -m "feat: ollama.ensure_ready — auto-spawn serve + ensure model (ask-once pull)"
```

---

## Task 6: Wire autostart into the REPL and one-shot CLI

**Files:**
- Modify: `any2md/repl.py` (`run`, around line 451)
- Modify: `any2md/cli.py` (`convert`, around line 80-88)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test (one-shot CLI calls ensure_ready)**

Add to `tests/test_cli.py`:

```python
def test_convert_calls_ollama_ensure_ready_when_provider_ollama(tmp_path, monkeypatch):
    import any2md.enrich.ollama as ollama
    from any2md import pipeline
    from typer.testing import CliRunner
    from any2md.cli import app

    called = {}
    monkeypatch.setattr(
        ollama, "ensure_ready",
        lambda interactive: called.setdefault("hit", True) or ("extractive", "note"),
    )
    monkeypatch.setattr(pipeline, "convert", lambda *a, **k: tmp_path / "x.md")
    (tmp_path / "x.md").write_text("# x\n")

    runner = CliRunner()
    result = runner.invoke(
        app, ["convert", "https://x.com/a", "-o", str(tmp_path), "--provider", "ollama"]
    )
    assert result.exit_code == 0
    assert called.get("hit") is True  # autostart attempted before converting
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/pytest tests/test_cli.py::test_convert_calls_ollama_ensure_ready_when_provider_ollama -v`
Expected: FAIL — `ensure_ready` is never called.

- [ ] **Step 3: Call ensure_ready in the one-shot CLI**

In `any2md/cli.py`, inside `convert`, the code currently builds `console` then loops. Right after the `console = Console()` line (around line 87), add:

```python
    if provider == "ollama":
        import sys

        from any2md.enrich import ollama

        provider, _note = ollama.ensure_ready(interactive=sys.stdin.isatty())
        if _note:
            console.print(f"  {_note}", style="dim")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_cli.py::test_convert_calls_ollama_ensure_ready_when_provider_ollama -v`
Expected: PASS

- [ ] **Step 5: Wire it into the REPL startup (no test — `run` is interactive/pragma no cover)**

In `any2md/repl.py`, in `run`, just after the first-run block (after the `if config.is_first_run(): await self._first_run(...)` lines, around line 453) and before `print_welcome(console)`, add:

```python
        if self.provider == "ollama":
            from any2md.enrich import ollama

            self.provider, _note = ollama.ensure_ready(interactive=sys.stdin.isatty())
            if _note:
                console.print(Text(f"  {_note}", style="dim"))
```

(`sys` is imported at module top; `Text` is imported inside `run`.)

- [ ] **Step 6: Run the full suite + lint**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`
Expected: all pass, no lint errors.

- [ ] **Step 7: Commit**

```bash
git add any2md/cli.py any2md/repl.py tests/test_cli.py
git commit -m "feat: auto-start ollama on REPL launch and one-shot convert when provider=ollama"
```

---

## Task 7: Manual verification

- [ ] **Step 1: Remote PDF converts (the reported bug)**

Run (real network):
```bash
.venv/bin/python -c "
import os, tempfile
os.environ['ANY2MD_CONFIG']=tempfile.mktemp(); os.environ['ANY2MD_STATS']=tempfile.mktemp()
from any2md import pipeline
out = pipeline.convert('https://arxiv.org/pdf/1706.03762', tempfile.mkdtemp(), 'none', on_event=print)
print('WROTE', out)
"
```
Expected: routes through `RemoteFileHandler`, prints `WROTE <path>.md` (not a "skipped" warning).

- [ ] **Step 2: Output dir persists**

Run:
```bash
.venv/bin/python -c "
import os, tempfile
os.environ['ANY2MD_CONFIG']=tempfile.mktemp()
from any2md.queue import JobQueue
from any2md.repl import Repl
from any2md import config
r = Repl(JobQueue(), output_dir='/tmp/x', provider='none')
r.handle('/output ~/MyVault')
print('persisted:', config.get('output_dir'))
"
```
Expected: `persisted: ~/MyVault`.

- [ ] **Step 3: Confirm everything is green**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`
Expected: all pass.

---

## Self-Review (completed)

- **Spec coverage:** Component A (remote files) → Tasks 2-3; Component B (ollama autostart, ask-once pull) → Tasks 4-6; Component C (sticky output + banner) → Task 1. All covered.
- **Placeholders:** none — every step has full code and exact commands.
- **Type consistency:** `SourceUnavailable` defined in Task 2 used in Tasks 3; `_download`, `_server_up`, `_list_models`, `_start_server`, `_pull_model`, `_ensure_model`, `ensure_ready` signatures match between implementation and tests; `ensure_ready` returns `(provider, note)` everywhere.
- **Scope note:** Explicit depth-threading through `queue.submit` (mentioned in the other spec) is intentionally NOT here — out of scope for usability.
```
