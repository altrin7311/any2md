"""Theme + drag-drop tests — pure logic (no terminal rendering assertions)."""

from any2md.repl import _clean_dropped_path
from any2md.theme import COMMANDS, GRADIENT, gradient_text


def test_gradient_text_preserves_content():
    t = gradient_text("Any2MD")
    assert t.plain == "Any2MD"


def test_gradient_has_cyan_to_purple_stops():
    assert GRADIENT[0].lower() == "#22d3ee"  # cyan start
    assert GRADIENT[-1].lower() == "#a855f7"  # purple end


def test_every_command_has_a_tip():
    assert len(COMMANDS) >= 6
    for name, tip in COMMANDS:
        assert name.startswith("/")
        assert tip and len(tip) > 5  # a real, non-empty tip


def test_clean_dropped_path_strips_single_quotes():
    assert _clean_dropped_path("'/Users/me/My File.pdf'") == "/Users/me/My File.pdf"


def test_clean_dropped_path_strips_double_quotes():
    assert _clean_dropped_path('"/Users/me/doc.pdf"') == "/Users/me/doc.pdf"


def test_clean_dropped_path_unescapes_spaces():
    # terminals escape spaces with a backslash on drag-drop
    assert _clean_dropped_path("/Users/me/My\\ File.pdf") == "/Users/me/My File.pdf"


def test_clean_dropped_path_leaves_urls_untouched():
    assert _clean_dropped_path("https://example.com/a") == "https://example.com/a"


def test_clean_dropped_path_leaves_plain_path():
    assert _clean_dropped_path("/tmp/note.txt") == "/tmp/note.txt"
