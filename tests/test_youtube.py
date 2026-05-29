"""YouTube handler tests — yt-dlp mocked, no live network."""

from unittest.mock import patch

from any2md.handlers.youtube import YouTubeHandler, _parse_vtt

_FAKE_INFO = {
    "title": "Transformers Explained",
    "channel": "AI Channel",
    "id": "dQw4w9WgXcQ",
    "upload_date": "20240115",
    "description": "A deep dive into the Transformer architecture and self-attention.",
    "duration": 900,
    "subtitles": {},
    "automatic_captions": {},
}


def test_youtube_matches_watch_url():
    assert YouTubeHandler().matches("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_youtube_matches_short_url():
    assert YouTubeHandler().matches("https://youtu.be/dQw4w9WgXcQ")


def test_youtube_matches_shorts_url():
    assert YouTubeHandler().matches("https://www.youtube.com/shorts/dQw4w9WgXcQ")


def test_youtube_does_not_match_file():
    assert not YouTubeHandler().matches("/tmp/video.mp4")


def test_youtube_does_not_match_other_url():
    assert not YouTubeHandler().matches("https://vimeo.com/123")


def test_youtube_extract_sets_document_fields():
    with patch("any2md.handlers.youtube._ydl_extract", return_value=_FAKE_INFO):
        doc = YouTubeHandler().extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert doc.title == "Transformers Explained"
    assert doc.source_type == "youtube"
    assert doc.source_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert doc.upload_date == "2024-01-15"
    assert doc.metadata["channel"] == "AI Channel"
    assert doc.metadata["video_id"] == "dQw4w9WgXcQ"
    assert doc.metadata["duration"] == 900


def test_youtube_extract_falls_back_to_description():
    with patch("any2md.handlers.youtube._ydl_extract", return_value=_FAKE_INFO):
        doc = YouTubeHandler().extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert "Transformer" in doc.body_markdown


_SAMPLE_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.000
hi everyone so by now you have

00:00:02.000 --> 00:00:04.000
hi everyone so by now you have
probably heard of chat GPT

00:00:04.000 --> 00:00:06.000
<c>it has taken the world by storm</c>
"""


def test_parse_vtt_strips_headers_and_timestamps():
    out = _parse_vtt(_SAMPLE_VTT)
    assert "WEBVTT" not in out
    assert "Kind:" not in out
    assert "Language:" not in out
    assert "-->" not in out
    assert "<c>" not in out  # inline cue tags stripped


def test_parse_vtt_dedups_rolling_lines():
    out = _parse_vtt(_SAMPLE_VTT)
    # the rolling-caption duplicate of "hi everyone..." must not appear twice
    assert out.count("hi everyone so by now you have") == 1
    assert "chat GPT" in out
    assert "taken the world by storm" in out
