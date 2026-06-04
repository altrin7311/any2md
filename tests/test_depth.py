"""Depth level mechanics — ratios, arrow navigation, config precedence, learned line hints."""

import any2md.depth as depth
from any2md import config, eta


def test_ratio_per_level():
    assert depth.ratio("low") == 0.10
    assert depth.ratio("medium") == 0.30
    assert depth.ratio("high") == 0.75


def test_bounds_are_tiered():
    assert depth.bounds("low") == (3, 6)
    assert depth.bounds("medium") == (8, 18)
    assert depth.bounds("high") == (16, 200)
    assert depth.bounds("unknown") == (8, 18)  # defaults to medium


def test_raw_level_exists_and_is_terminal():
    assert "raw" in depth.LEVELS
    assert depth.next_level("raw") == "raw"  # can't go higher than raw
    assert depth.prev_level("raw") == "high"


def test_is_raw():
    assert depth.is_raw("raw") is True
    assert depth.is_raw("high") is False
    assert depth.is_raw("medium") is False


def test_levels_order():
    assert depth.LEVELS == ["low", "medium", "high", "raw"]


def test_next_level_advances_and_clamps():
    assert depth.next_level("low") == "medium"
    assert depth.next_level("medium") == "high"
    assert depth.next_level("high") == "raw"
    assert depth.next_level("raw") == "raw"  # clamp at top


def test_prev_level_retreats_and_clamps():
    assert depth.prev_level("raw") == "high"
    assert depth.prev_level("high") == "medium"
    assert depth.prev_level("medium") == "low"
    assert depth.prev_level("low") == "low"  # clamp at bottom


def test_config_depth_defaults_to_medium(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.delenv("ANY2MD_DEPTH", raising=False)
    assert config.get("depth") == "medium"


def test_config_depth_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    monkeypatch.delenv("ANY2MD_DEPTH", raising=False)
    config.set_value("depth", "high")
    assert config.get("depth") == "high"


def test_env_overrides_config_depth(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_CONFIG", str(tmp_path / "c.toml"))
    config.set_value("depth", "low")
    monkeypatch.setenv("ANY2MD_DEPTH", "high")
    assert config.get("depth") == "high"


def test_estimate_lines_falls_back_to_heuristic(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_STATS", str(tmp_path / "s.json"))
    assert eta.estimate_lines("low") == 10
    assert eta.estimate_lines("medium") == 40
    assert eta.estimate_lines("high") == 80
    assert eta.estimate_lines("raw") == 0  # N/A: full content passthrough


def test_record_lines_learns(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2MD_STATS", str(tmp_path / "s.json"))
    eta.record_lines("medium", 40)
    # EMA pulls the estimate toward the observation, above the static 15.
    assert eta.estimate_lines("medium") > 15
