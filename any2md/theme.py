"""Glowing Cyan→Purple theme — banner, gradient text, command palette with tips.

Claude-Code-style polish: a gradient wordmark, per-command color highlight, and a tip
for every command. Pure Rich; degrades to plain text on dumb terminals.
"""

from rich.console import Console, Group
from rich.text import Text

from any2md import depth as _depth

# Cyan → sky → indigo → violet → purple. Matches the /effort "Max" glow direction.
GRADIENT = ["#22D3EE", "#38BDF8", "#6366F1", "#8B5CF6", "#A855F7"]

# (command, tip). Every command carries a one-line tip, shown in the banner and /help.
COMMANDS: list[tuple[str, str]] = [
    ("/output <dir>", "set where .md files are written (drag a folder in)"),
    ("/provider <name>", "switch summarizer: extractive · ollama · none"),
    ("/depth", "set summary depth: low · medium · high (◀ ▶ to pick)"),
    ("/batch <file>", "convert every link/path in a file, one per line"),
    ("/jobs", "see queued / running / done jobs with live status"),
    ("/last", "print the path of the most recently written .md"),
    ("/open [last]", "open the output folder (or the last note) in your file viewer"),
    ("/rename <name>", "rename the file you just made (the slug is auto-cleaned)"),
    ("/help", "show this command palette"),
    ("/quit", "exit Any2MD"),
]

# One rotating tip shown at boot (replaces the static command palette on startup).
BOOT_TIPS: list[str] = [
    "Paste any URL or file to convert it  ·  /help for all commands",
    "Try /depth to control how much gets summarized  ·  /help for commands",
    "/batch <file> converts a whole list of links at once",
    "/provider ollama switches to your local Ollama for richer summaries",
    "/rename <name> renames the last file you created",
]

# Faded tips shown while a conversion runs (rotated every few seconds).
CONVERTING_TIPS: list[str] = [
    "drag a file straight into the terminal to convert it",
    "paste any link — YouTube, Reddit, GitHub, arXiv, Wikipedia, HN, Stack Overflow, X",
    "summaries run locally — nothing leaves your machine",
    "rename the result with /rename <better title>",
    "run Ollama and Any2MD uses it automatically for richer summaries",
    "/batch <file> converts a whole list of links at once",
]

# Tips surfaced occasionally at the prompt across a session.
SESSION_TIPS: list[str] = [
    "Tip: change where files land any time with /output <dir>.",
    "Tip: /jobs shows everything queued, running, and done.",
    "Tip: /last prints the path of the file you just made.",
    "Tip: /provider none gives extraction-only, no summary.",
    "Tip: drop a folder onto /output to retarget your vault.",
]

# Logo palettes: ANY rides a full rainbow, the "2" is an arrow (converting → md), MD is cyan.
RAINBOW = ["#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#22D3EE", "#AF52FF"]
ARROW_STOPS = ["#FF2EC4", "#8B5CF6", "#22D3EE"]  # magenta → violet → cyan, flows into MD
CYAN = "#22D3EE"

# "ANY" — rainbow.  width 27 per row (A=8 + N=10 + Y=9).
_ANY = [
    " █████╗ ███╗   ██╗██╗   ██╗",
    "██╔══██╗████╗  ██║╚██╗ ██╔╝",
    "███████║██╔██╗ ██║ ╚████╔╝ ",
    "██╔══██║██║╚██╗██║  ╚██╔╝  ",
    "██║  ██║██║ ╚████║   ██║   ",
    "╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ",
]

# The "2" — a normal-width digit whose base ends in a subtle ▶ tip (converting, aimed at MD).
# Kept at width 8 so the gap to "MD" is the same as a plain "2".
_ARROW = [
    "██████╗ ",
    "╚════██╗",
    " █████╔╝",
    "██╔═══╝ ",
    "███████▶",
    "╚══════╝",
]

# "MD" — cyan.  width 19 per row (M=11 + D=8).
_MD = [
    "███╗   ███╗██████╗ ",
    "████╗ ████║██╔══██╗",
    "██╔████╔██║██║  ██║",
    "██║╚██╔╝██║██║  ██║",
    "██║ ╚═╝ ██║██████╔╝",
    "╚═╝     ╚═╝╚═════╝ ",
]


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    r = round(a[0] + (b[0] - a[0]) * t)
    g = round(a[1] + (b[1] - a[1]) * t)
    bl = round(a[2] + (b[2] - a[2]) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


def _grad_color(t: float, stops: list[str]) -> str:
    """Color at position t in [0,1] along an arbitrary list of hex stops."""
    pts = [_hex_to_rgb(c) for c in stops]
    if t <= 0:
        return stops[0]
    if t >= 1:
        return stops[-1]
    span = 1 / (len(pts) - 1)
    idx = min(int(t / span), len(pts) - 2)
    local = (t - idx * span) / span
    return _lerp(pts[idx], pts[idx + 1], local)


def _color_at(t: float) -> str:
    """Color at position t along the default cyan→purple gradient."""
    return _grad_color(t, GRADIENT)


def depth_hint(level: str, lines: int) -> str:
    """Greyed sub-line for the /depth picker: how much of the source this level keeps."""
    if level == "raw":
        return "full source · no summarization"
    pct = round(_depth.ratio(level) * 100)
    return f"~{pct}% of source · ~{lines} lines"


def depth_bar(level: str) -> Text:
    """A scroll-bar from low to raw with the knob at the current level (cyan→purple)."""
    idx = _depth.LEVELS.index(level) if level in _depth.LEVELS else 1
    track = ["─"] * (len(_depth.LEVELS) * 2 - 1)
    track[idx * 2] = "●"
    first = _depth.LEVELS[0]
    last = _depth.LEVELS[-1]
    bar = Text(f"  {first} ", style="dim")
    for i, ch in enumerate(track):
        bar.append(ch, style=_color_at(i / (len(track) - 1)) + (" bold" if ch == "●" else ""))
    bar.append(f" {last}   ", style="dim")
    bar.append(level, style="#A855F7 bold")
    return bar


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


def _grad_segment(text: Text, s: str, stops: list[str]) -> None:
    n = max(len(s) - 1, 1)
    for i, ch in enumerate(s):
        text.append(ch, style=_grad_color(i / n, stops) + " bold")


def banner() -> Group:
    """The wordmark — rainbow ANY, arrow-2 converting toward, cyan MD — plus a tagline."""
    rendered = []
    for i in range(len(_ANY)):
        line = Text("  ")
        _grad_segment(line, _ANY[i], RAINBOW)  # ANY → rainbow
        line.append("  ")
        _grad_segment(line, _ARROW[i], ARROW_STOPS)  # 2 → arrow, magenta→cyan
        line.append("  ")
        line.append(_MD[i], style=CYAN + " bold")  # MD → cyan
        rendered.append(line)
    rendered.append(Text("  anything → Obsidian markdown · every input summarized", style="dim"))
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


def print_welcome(console: Console, _tip_idx: int | None = None) -> None:
    import random

    console.print(banner())
    console.print()
    idx = _tip_idx if _tip_idx is not None else random.randrange(len(BOOT_TIPS))
    tip = BOOT_TIPS[idx % len(BOOT_TIPS)]
    console.print(Text(f"  {tip}", style="dim"))
    console.print()
