"""Interactive REPL — paste links/paths, change config live, run batches.

Command handling (`handle`) is pure and synchronous so it can be tested without an event
loop; the async `run` loop wires real stdin + Rich progress around it.
"""

import asyncio
from pathlib import Path

from any2md.queue import JobQueue

_COMMANDS = {"/output", "/provider", "/batch", "/jobs", "/last", "/help", "/quit"}

# Status → Rich color, tracking the cyan→purple theme.
_STATUS_STYLE = {
    "queued": "dim",
    "extracting": "#22D3EE",
    "enriching": "#6366F1",
    "writing": "#8B5CF6",
    "done": "#A855F7 bold",
    "error": "red bold",
}


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


class Repl:
    def __init__(self, queue: JobQueue, output_dir: str, provider: str):
        self.queue = queue
        self.output_dir = output_dir
        self.provider = provider
        self.running = True

    def handle(self, line: str) -> str | None:
        """Process one input line. Returns text to print, or None for quit/no output."""
        line = line.strip()
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
            self.output_dir = _clean_dropped_path(arg)
            return f"output_dir set to {self.output_dir}"
        if cmd == "/provider":
            if not arg:
                return f"provider = {self.provider}"
            self.provider = arg
            return f"provider set to {arg}"
        if cmd == "/batch":
            return self._batch(arg)
        if cmd == "/jobs":
            return self._jobs()
        if cmd == "/last":
            return self._last()
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

    async def run(self) -> None:  # pragma: no cover - interactive loop
        from rich.console import Console

        from any2md.theme import gradient_text, print_welcome

        console = Console()
        await self.queue.start()
        print_welcome(console)
        prompt = gradient_text("any2md", bold=True)
        prompt.append(" › ", style="#A855F7 bold")
        loop = asyncio.get_event_loop()
        while self.running:
            console.print(prompt, end="")
            try:
                line = await loop.run_in_executor(None, input, "")
            except (EOFError, KeyboardInterrupt):
                break
            out = self.handle(line)
            if out:
                console.print(out)
        await self.queue.stop()
