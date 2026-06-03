"""Config load/save for Any2MD.

Stored in ``~/.any2md/config.toml`` (override path with ``ANY2MD_CONFIG``).
Precedence for reads: env var > config.toml > built-in default.
API keys are NEVER written here — they come from env vars only.
"""

import os
import tomllib
from pathlib import Path

import tomli_w

DEFAULTS: dict[str, object] = {
    "output_dir": "~/Any2MD-out",
    "provider": "extractive",  # free, zero-setup summaries; "ollama" or "none" also valid
    "whisper_fallback": False,
    "depth": "medium",  # summary depth: low|medium|high — fraction of source kept (see depth.py)
    "ollama_autopull": None,  # None = ask once before a large model pull; True/False remembers it
}

# User-facing aliases → canonical config key.
_ALIASES = {"output": "output_dir"}

_BOOL_KEYS = {"whisper_fallback"}


def config_path() -> Path:
    return Path(os.environ.get("ANY2MD_CONFIG", "~/.any2md/config.toml")).expanduser()


def is_first_run() -> bool:
    """No config file yet → this is the user's first launch (trigger onboarding)."""
    return not config_path().exists()


def _canonical(key: str) -> str:
    key = _ALIASES.get(key, key)
    if key not in DEFAULTS:
        raise ValueError(f"unknown config key: {key!r} (allowed: {sorted(DEFAULTS)})")
    return key


def _coerce(key: str, value: object) -> object:
    if key in _BOOL_KEYS and isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return value


def _read_file() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text())


def _write_file(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(data))


def get(key: str) -> object:
    key = _canonical(key)
    env = os.environ.get("ANY2MD_" + key.upper())
    if env is not None:
        return _coerce(key, env)
    data = _read_file()
    if key in data:
        return data[key]
    return DEFAULTS[key]


def set_value(key: str, value: object) -> None:
    key = _canonical(key)  # raises ValueError on unknown/secret keys
    data = _read_file()
    data[key] = _coerce(key, value)
    _write_file(data)


def effective() -> dict[str, object]:
    return {key: get(key) for key in DEFAULTS}
