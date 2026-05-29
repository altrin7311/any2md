"""Conversion-time estimates: per-source heuristics that learn from real runs.

First run has no history, so we start from a hand-tuned per-source estimate and blend it
toward observed durations (exponential moving average) stored in ``~/.any2md/stats.json``
(override path with ``ANY2MD_STATS``). Network sources are slower than local files.
"""

import json
import os
from pathlib import Path

# Seconds. Rough first-run guesses; learning corrects them per machine/connection.
_HEURISTIC = {
    "file": 2.0,
    "web": 5.0,
    "reddit": 6.0,
    "github": 5.0,
    "youtube": 25.0,  # caption fetch dominates
    "arxiv": 4.0,
    "wikipedia": 3.0,
    "hackernews": 8.0,  # one request per comment
    "stackoverflow": 6.0,
    "twitter": 4.0,
}
_DEFAULT = 6.0
_ALPHA = 0.3  # EMA weight on the newest observation

# Static first-run guesses for how many lines a depth level produces; learning corrects them.
_LINE_HEURISTIC = {"low": 10, "medium": 40, "high": 80}


def _stats_path() -> Path:
    return Path(os.environ.get("ANY2MD_STATS", "~/.any2md/stats.json")).expanduser()


def _load() -> dict:
    path = _stats_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    path = _stats_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def classify(target: str) -> str:
    """Source type for a target, without extracting it (cheap matches() probe)."""
    from any2md.registry import _HANDLERS

    for handler in _HANDLERS:
        if handler.matches(target):
            return handler.source_type
    return "unknown"


def estimate(source_type: str) -> float:
    """Best current estimate (learned EMA if present, else heuristic)."""
    learned = _load().get(source_type)
    if learned is not None:
        return float(learned)
    return _HEURISTIC.get(source_type, _DEFAULT)


def record(source_type: str, seconds: float) -> None:
    """Fold an observed duration into the running estimate for this source."""
    data = _load()
    prior = data.get(source_type, _HEURISTIC.get(source_type, _DEFAULT))
    data[source_type] = round(_ALPHA * seconds + (1 - _ALPHA) * prior, 2)
    _save(data)


def estimate_lines(level: str) -> int:
    """Best current guess for how many lines a depth level yields (learned EMA else heuristic).
    Used by the /depth picker's greyed hint. Returns 0 for 'raw' (full passthrough)."""
    if level == "raw":
        return 0
    learned = _load().get(f"lines_{level}")
    if learned is not None:
        return round(float(learned))
    return _LINE_HEURISTIC.get(level, _LINE_HEURISTIC["medium"])


def record_lines(level: str, n: int) -> None:
    """Fold an observed output line count into the running per-level estimate."""
    data = _load()
    prior = data.get(f"lines_{level}", _LINE_HEURISTIC.get(level, _LINE_HEURISTIC["medium"]))
    data[f"lines_{level}"] = round(_ALPHA * n + (1 - _ALPHA) * prior, 2)
    _save(data)
