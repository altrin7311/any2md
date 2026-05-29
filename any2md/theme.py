"""Glowing Cyan→Purple theme — banner, gradient text, command palette with tips.

Claude-Code-style polish: a gradient wordmark, per-command color highlight, and a tip
for every command. Pure Rich; degrades to plain text on dumb terminals.
"""

from rich.console import Console, Group
from rich.text import Text

# Cyan → sky → indigo → violet → purple. Matches the /effort "Max" glow direction.
GRADIENT = ["#22D3EE", "#38BDF8", "#6366F1", "#8B5CF6", "#A855F7"]

# (command, tip). Every command carries a one-line tip, shown in the banner and /help.
COMMANDS: list[tuple[str, str]] = [
    ("/output <dir>", "set where .md files are written (drag a folder in)"),
    ("/provider <name>", "switch summarizer: extractive · ollama · none"),
    ("/batch <file>", "convert every link/path in a file, one per line"),
    ("/jobs", "see queued / running / done jobs with live status"),
    ("/last", "print the path of the most recently written .md"),
    ("/help", "show this command palette"),
    ("/quit", "exit Any2MD"),
]

_BANNER = r"""
 █████╗ ███╗   ██╗██╗   ██╗██████╗ ███╗   ███╗██████╗
██╔══██╗████╗  ██║╚██╗ ██╔╝╚════██╗████╗ ████║██╔══██╗
███████║██╔██╗ ██║ ╚████╔╝  █████╔╝██╔████╔██║██║  ██║
██╔══██║██║╚██╗██║  ╚██╔╝  ██╔═══╝ ██║╚██╔╝██║██║  ██║
██║  ██║██║ ╚████║   ██║   ███████╗██║ ╚═╝ ██║██████╔╝
╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝     ╚═╝╚═════╝"""


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    r = round(a[0] + (b[0] - a[0]) * t)
    g = round(a[1] + (b[1] - a[1]) * t)
    bl = round(a[2] + (b[2] - a[2]) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


def _color_at(t: float) -> str:
    """Color at position t in [0,1] along the gradient stops."""
    stops = [_hex_to_rgb(c) for c in GRADIENT]
    if t <= 0:
        return GRADIENT[0]
    if t >= 1:
        return GRADIENT[-1]
    span = 1 / (len(stops) - 1)
    idx = min(int(t / span), len(stops) - 2)
    local = (t - idx * span) / span
    return _lerp(stops[idx], stops[idx + 1], local)


def gradient_text(s: str, bold: bool = False) -> Text:
    """Per-character gradient across the cyan→purple stops."""
    text = Text()
    n = max(len(s) - 1, 1)
    for i, ch in enumerate(s):
        style = _color_at(i / n)
        if bold:
            style += " bold"
        text.append(ch, style=style)
    return text


def banner() -> Group:
    """The gradient wordmark + tagline, ready to print."""
    lines = [ln for ln in _BANNER.splitlines() if ln]
    rendered = [gradient_text(ln, bold=True) for ln in lines]
    tagline = Text("  anything → Obsidian markdown · every input summarized", style="dim")
    rendered.append(tagline)
    return Group(*rendered)


def command_palette() -> Group:
    """Each command highlighted with its color + a dim tip — the /help view."""
    rows = []
    n = max(len(COMMANDS) - 1, 1)
    for i, (cmd, tip) in enumerate(COMMANDS):
        line = Text("  ")
        line.append(f"{cmd:<18}", style=_color_at(i / n) + " bold")
        line.append(tip, style="dim")
        rows.append(line)
    return Group(*rows)


def print_welcome(console: Console) -> None:
    console.print(banner())
    console.print()
    console.print(gradient_text("  Commands", bold=True))
    console.print(command_palette())
    console.print()
    console.print(
        Text("  Paste or drag in a link or file to convert it.", style="dim"),
    )
    console.print()
