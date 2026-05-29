"""Summary depth: how much of a source to keep. low/medium/high → fraction of the source.

Pure level math (no IO). The chosen level lives in config (`depth` key); learned line-count
hints for the /depth picker live in eta.py's stats file.
"""

LEVELS = ["low", "medium", "high", "raw"]
RATIOS = {"low": 0.10, "medium": 0.30, "high": 0.50}


def ratio(level: str) -> float:
    return RATIOS.get(level, RATIOS["medium"])


def is_raw(level: str) -> bool:
    return level == "raw"


def next_level(level: str) -> str:
    i = LEVELS.index(level) if level in LEVELS else 1
    return LEVELS[min(i + 1, len(LEVELS) - 1)]


def prev_level(level: str) -> str:
    i = LEVELS.index(level) if level in LEVELS else 1
    return LEVELS[max(i - 1, 0)]
