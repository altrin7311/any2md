"""Interactive REPL — paste links/paths, change config live, run batches.

Command handling (`handle`) is pure and synchronous so it can be tested without an event
loop; the async `run` loop wires real stdin + Rich progress around it.
"""

import asyncio
import sys
from pathlib import Path

from any2md.queue import JobQueue

_COMMANDS = {
    "/output",
    "/provider",
    "/depth",
    "/batch",
    "/jobs",
    "/last",
    "/open",
    "/rename",
    "/help",
    "/quit",
}

_PROVIDERS = ("extractive", "ollama", "none")

# Status → Rich color, tracking the cyan→purple theme.
_STATUS_STYLE = {
    "queued": "dim",
    "extracting": "#22D3EE",
    "enriching": "#6366F1",
    "writing": "#8B5CF6",
    "done": "#A855F7 bold",
    "skipped": "#F59E0B",
    "error": "red bold",
}

_INVOCATION_PREFIXES = ("any2md convert ", "any2md ", "convert ")

# prompt_toolkit prompt: "any2md" cyan-bold + " › " purple-bold
_PT_PROMPT = [("bold fg:#22D3EE", "any2md"), ("bold fg:#A855F7", " › ")]


def _strip_invocation_prefix(line: str) -> str:
    """Drop a leading 'any2md convert' / 'convert' that users type out of habit."""
    for prefix in _INVOCATION_PREFIXES:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return line


def _clean_dropped_path(line: str) -> str:
    """Normalize a drag-and-dropped path: strip surrounding quotes, unescape '\\ ' spaces."""
    s = line.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    if s.startswith(("http://", "https://")):
        return s
    return s.replace("\\ ", " ")


def _looks_convertible(line: str) -> bool:
    if line.startswith(("http://", "https://")):
        return True
    return Path(line).expanduser().exists()


def display_name(path: Path, shown_full_already: bool) -> str:
    """Full path on the first conversion of a session (so new users find their vault),
    then just the basename to keep later lines compact."""
    return path.name if shown_full_already else str(path)


def tldr_peek(markdown: str) -> str:
    """Pull the TL;DR text out of a rendered note so the REPL can show a one-glance preview.
    Returns "" when the note has no summary callout (passthrough / provider=none)."""
    lines: list[str] = []
    in_summary = False
    for line in markdown.splitlines():
        if line.startswith("> [!summary]"):
            in_summary = True
            continue
        if in_summary:
            if line.startswith(">"):
                lines.append(line.lstrip(">").strip())
            else:
                break
    return " ".join(part for part in lines if part).strip()


def _opener_cmd(platform: str) -> str:
    """The OS file-opener command for the current platform."""
    if platform == "darwin":
        return "open"
    if platform.startswith("win"):
        return "start"
    return "xdg-open"


# ── prompt_toolkit helpers ─────────────────────────────────────────────────────


def _make_lexer():  # pragma: no cover
    """Colors /commands while typing: cyan=valid, purple=partial, red=unknown."""
    from prompt_toolkit.lexers import Lexer

    class _CmdLexer(Lexer):
        def lex_document(self, document):
            def get_line(lineno):
                line = document.lines[lineno]
                if not line.startswith("/"):
                    return [("", line)]
                cmd = line.split()[0] if line.split() else line
                if cmd in _COMMANDS:
                    rest = line[len(cmd) :]
                    return [("bold fg:#22D3EE", cmd), ("", rest)]
                if any(c.startswith(cmd) for c in _COMMANDS):
                    return [("bold fg:#A855F7", line)]
                return [("bold fg:#FF5555", line)]

            return get_line

    return _CmdLexer()


def _make_auto_suggest():  # pragma: no cover
    """Ghost-text inline suggestion: type /dep → see 'th' greyed out; Tab fills it."""
    from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion

    class _CmdSuggest(AutoSuggest):
        def get_suggestion(self, buffer, document):
            text = document.text_before_cursor.lstrip()
            if text.startswith("/") and len(text) > 1 and " " not in text:
                for cmd in sorted(_COMMANDS):
                    if cmd.startswith(text) and cmd != text:
                        return Suggestion(cmd[len(text) :])
            return None

    return _CmdSuggest()


def _make_keybindings():  # pragma: no cover
    """Tab accepts ghost-text suggestion; other keys use prompt_toolkit defaults."""
    from prompt_toolkit.key_binding import KeyBindings

    kb = KeyBindings()

    @kb.add("tab")
    def _accept(event):
        buf = event.app.current_buffer
        if buf.suggestion:
            buf.insert_text(buf.suggestion.text)

    return kb


class Repl:
    def __init__(self, queue: JobQueue, output_dir: str, provider: str):
        from any2md import config

        self.queue = queue
        self.output_dir = output_dir
        self.provider = provider
        self.depth = str(config.get("depth"))  # summary depth: low|medium|high|raw
        self.running = True
        self._shown_full_path = False  # show the full output path once, basename after

    def handle(self, line: str) -> str | None:
        """Process one input line. Returns text to print, or None for quit/no output."""
        line = _strip_invocation_prefix(line.strip())
        if not line:
            return ""

        if line.split(maxsplit=1)[0] in _COMMANDS:
            return self._command(line)

        target = _clean_dropped_path(line)
        if _looks_convertible(target):
            jid = self.queue.submit(target, self.output_dir, self.provider)
            return f"queued job {jid}: {target}"

        return f"unrecognized input (not a URL or existing path): {line}"

    def _command(self, line: str) -> str | None:
        parts = line.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/quit":
            self.running = False
            return None
        if cmd == "/help":
            from any2md.theme import COMMANDS

            lines = ["Paste or drag in a link or file to convert it. Commands:"]
            lines += [f"  {name:<18}{tip}" for name, tip in COMMANDS]
            return "\n".join(lines)
        if cmd == "/output":
            if not arg:
                return f"output_dir = {self.output_dir}"
            from any2md import config

            self.output_dir = _clean_dropped_path(arg)
            config.set_value("output_dir", self.output_dir)
            return f"output_dir set to {self.output_dir}"
        if cmd == "/provider":
            return self._set_provider(arg)
        if cmd == "/depth":
            return self._set_depth(arg)
        if cmd == "/batch":
            return self._batch(arg)
        if cmd == "/jobs":
            return self._jobs()
        if cmd == "/last":
            return self._last()
        if cmd == "/open":
            return self._open(arg)
        if cmd == "/rename":
            return self._rename(arg)
        return f"unknown command: {cmd} (try /help)"

    def _batch(self, arg: str) -> str:
        path = Path(_clean_dropped_path(arg)).expanduser()
        if not path.exists():
            return f"batch file not found: {arg}"
        targets = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
        for target in targets:
            self.queue.submit(target, self.output_dir, self.provider)
        return f"queued {len(targets)} job(s)"

    def _jobs(self) -> str:
        jobs = self.queue.all()
        if not jobs:
            return "no jobs yet"
        rows = []
        for j in jobs:
            style = _STATUS_STYLE.get(j.status, "")
            status = f"[{style}]{j.status:<11}[/{style}]" if style else f"{j.status:<11}"
            rows.append(f"  {j.id}  {status}  {j.target}")
        return "\n".join(rows)

    def _last(self) -> str:
        done = [j for j in self.queue.all() if j.result is not None]
        if not done:
            return "no completed jobs yet"
        return str(done[-1].result)

    def _open(self, arg: str) -> str:
        """Open the last note (`/open last`) or the output folder (`/open`) in the OS viewer."""
        import subprocess

        if arg == "last":
            done = [j for j in self.queue.all() if j.result is not None]
            if not done:
                return "nothing converted yet"
            target = done[-1].result
        else:
            target = Path(self.output_dir).expanduser()
        subprocess.Popen([_opener_cmd(sys.platform), str(target)])
        return f"opening {target}"

    def _rename(self, arg: str) -> str:
        if not arg:
            return "usage: /rename <new title>"
        done = [j for j in self.queue.all() if j.result is not None]
        if not done:
            return "nothing to rename yet — convert something first"
        from any2md import writer

        job = done[-1]
        new_path = writer.rename_output(job.result, arg)
        job.result = new_path
        return f"renamed → {new_path.name}"

    def _set_provider(self, arg: str) -> str:
        from any2md import config

        if not arg:
            return f"provider = {self.provider}  (extractive · ollama · none)"
        if arg not in _PROVIDERS:
            return f"usage: /provider <extractive|ollama|none> (got {arg!r})"
        self.provider = arg
        config.set_value("provider", arg)
        return f"provider set to {arg}"

    def _set_depth(self, arg: str) -> str:
        from any2md import config, depth, eta
        from any2md.theme import depth_hint

        if not arg:
            return f"depth = {self.depth}  (low · medium · high · raw)"
        if arg not in depth.LEVELS:
            return f"usage: /depth <low|medium|high|raw> (got {arg!r})"
        self.depth = arg
        config.set_value("depth", arg)
        return f"depth set to {arg} · {depth_hint(arg, eta.estimate_lines(arg))}"

    async def _depth_picker(self, console) -> None:  # pragma: no cover - interactive raw input
        """Live ◀ ▶ depth selector (Claude /effort-style) using prompt_toolkit Application."""
        import io

        from prompt_toolkit import Application
        from prompt_toolkit.formatted_text import ANSI
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout, Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from rich.console import Console as RichConsole
        from rich.text import Text as RichText

        from any2md import config, depth, eta
        from any2md.theme import depth_bar, depth_hint

        level = [self.depth]
        committed = [False]

        def render():
            buf = io.StringIO()
            rc = RichConsole(file=buf, force_terminal=True, no_color=False, width=80)
            rc.print(RichText("  summary depth", style="bold"))
            rc.print(depth_bar(level[0]))
            hint = depth_hint(level[0], eta.estimate_lines(level[0]))
            rc.print(
                RichText(
                    f"     {hint}  ·  ◀ ▶ change  ·  enter confirm  ·  esc cancel",
                    style="dim",
                )
            )
            return ANSI(buf.getvalue())

        kb = KeyBindings()

        @kb.add("right")
        def _right(event):
            level[0] = depth.next_level(level[0])
            event.app.invalidate()

        @kb.add("left")
        def _left(event):
            level[0] = depth.prev_level(level[0])
            event.app.invalidate()

        @kb.add("enter")
        def _enter(event):
            committed[0] = True
            event.app.exit()

        @kb.add("escape")
        @kb.add("c-c")
        @kb.add("q")
        def _cancel(event):
            event.app.exit()

        app = Application(
            layout=Layout(Window(FormattedTextControl(render, focusable=True))),
            key_bindings=kb,
            full_screen=False,
            erase_when_done=True,
        )
        await app.run_async()

        if committed[0]:
            self.depth = level[0]
            config.set_value("depth", level[0])
            hint = depth_hint(level[0], eta.estimate_lines(level[0]))
            console.print(RichText(f"  depth → {level[0]}  ·  {hint}", style="dim"))

    async def _first_run(self, console, loop) -> None:  # pragma: no cover - interactive
        from rich.text import Text

        from any2md import config, onboarding
        from any2md.theme import gradient_text

        console.print(gradient_text("  Welcome to Any2MD", bold=True))
        console.print(Text("  Where should your .md files be saved?", style="bold"))
        console.print(
            Text("  (press Enter for ~/Any2MD-out — drag a folder in to set it)", style="dim")
        )
        raw = await loop.run_in_executor(None, input, "  output dir › ")
        chosen = _clean_dropped_path(raw.strip()) or "~/Any2MD-out"
        provider = onboarding.apply_first_run(chosen)
        self.output_dir = str(config.get("output_dir"))
        self.provider = provider
        note = (
            "found a local Ollama — using it for richer summaries"
            if provider == "ollama"
            else "using built-in extractive summaries (zero setup, fully offline)"
        )
        console.print(Text(f"  ✓ saved to {self.output_dir} · {note}", style="dim"))
        console.print()

    async def _convert_with_progress(self, console, target) -> None:  # pragma: no cover
        import time

        from rich.console import Group
        from rich.live import Live
        from rich.text import Text

        from any2md import eta
        from any2md.theme import CONVERTING_TIPS, gradient_text

        source = eta.classify(target)
        est = eta.estimate(source)
        job = self.queue.get(self.queue.submit(target, self.output_dir, self.provider))

        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        start = time.monotonic()
        i = 0
        with Live(console=console, refresh_per_second=12, transient=True) as live:
            while not job.done.is_set():
                elapsed = time.monotonic() - start
                remaining = max(est - elapsed, 0)
                eta_txt = f"~{remaining:.0f}s left" if remaining >= 1 else "finishing…"
                tip = CONVERTING_TIPS[int(elapsed // 3) % len(CONVERTING_TIPS)]
                head = Text()
                head.append(f"  {frames[i % len(frames)]} ", style="#22D3EE bold")
                head.append(f"converting {source}", style="#A855F7 bold")
                head.append(f"  ·  {eta_txt}", style="dim")
                live.update(Group(head, Text(f"     {tip}", style="dim italic")))
                i += 1
                await asyncio.sleep(0.08)

        eta.record(source, time.monotonic() - start)
        if job.error:
            console.print(Text(f"  ✗ {job.error}", style="red"))
        elif job.result:
            line = gradient_text("  ✓ ", bold=True)
            line.append(display_name(job.result, self._shown_full_path), style="bold")
            line.append("   /rename to change the name", style="dim")
            console.print(line)
            self._shown_full_path = True
            peek = tldr_peek(job.result.read_text())
            if peek:  # one-glance preview so the user trusts it without opening Obsidian
                console.print(Text(f"     {peek[:200]}", style="dim italic"))
            for warning in job.warnings:
                console.print(Text(f"  ⚠ {warning}", style="#F59E0B"))
        else:  # skipped — nothing written (empty/paywalled source); show why
            for warning in job.warnings:
                console.print(Text(f"  ⚠ {warning}", style="#F59E0B"))

    async def run(self) -> None:  # pragma: no cover - interactive loop
        from prompt_toolkit import PromptSession
        from prompt_toolkit.formatted_text import FormattedText
        from rich.console import Console
        from rich.text import Text

        from any2md import config
        from any2md.theme import SESSION_TIPS, print_welcome

        console = Console()
        loop = asyncio.get_event_loop()
        await self.queue.start()

        if config.is_first_run():
            await self._first_run(console, loop)

        if self.provider == "ollama":
            from any2md.enrich import ollama

            self.provider, _note = ollama.ensure_ready(interactive=sys.stdin.isatty())
            if _note:
                console.print(Text(f"  {_note}", style="dim"))

        print_welcome(console)
        console.print(Text(f"  output: {self.output_dir}", style="dim"))

        session = PromptSession(
            lexer=_make_lexer(),
            auto_suggest=_make_auto_suggest(),
            key_bindings=_make_keybindings(),
        )
        prompt_msg = FormattedText(_PT_PROMPT)

        turns = 0
        while self.running:
            try:
                line = await session.prompt_async(prompt_msg)
            except (EOFError, KeyboardInterrupt):
                break

            stripped = _strip_invocation_prefix(line.strip())
            if not stripped:
                continue
            turns += 1

            first = stripped.split(maxsplit=1)[0]
            if first == "/depth" and stripped == "/depth" and sys.stdin.isatty():
                await self._depth_picker(console)
            elif first in _COMMANDS:
                out = self.handle(line)
                if out:
                    console.print(out)
                if out is None:  # /quit
                    break
            else:
                target = _clean_dropped_path(stripped)
                if _looks_convertible(target):
                    try:
                        await self._convert_with_progress(console, target)
                    except KeyboardInterrupt:  # Ctrl-C cancels this convert, not the whole REPL
                        console.print(Text("  cancelled — back to prompt", style="dim"))
                else:
                    console.print(Text(f"  unrecognized: {stripped}", style="dim"))

            # An occasional faded tip, Claude-Code style.
            if turns % 4 == 0:
                tip = SESSION_TIPS[(turns // 4 - 1) % len(SESSION_TIPS)]
                console.print(Text(f"  {tip}", style="dim italic"))

        await self.queue.stop()
