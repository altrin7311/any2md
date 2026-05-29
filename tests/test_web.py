"""Web handler tests — trafilatura mocked via _fetch_and_extract."""

from unittest.mock import patch

from any2md.handlers.web import WebHandler

_FAKE_RESULT = {
    "text": "Transformers revolutionized NLP by replacing recurrent networks with self-attention. "
    "The architecture scales to billions of parameters. BERT and GPT are based on Transformers.",
    "title": "The Transformer Architecture Explained",
    "author": "Jane Doe",
    "date": "2024-03-15",
    "sitename": "example.com",
}


def test_web_matches_http():
    assert WebHandler().matches("http://example.com/article")


def test_web_matches_https():
    assert WebHandler().matches("https://example.com/article")


def test_web_does_not_match_file():
    assert not WebHandler().matches("/home/user/file.html")


def test_web_extract_document_fields():
    with patch("any2md.handlers.web._fetch_and_extract", return_value=_FAKE_RESULT):
        doc = WebHandler().extract("https://example.com/article")

    assert doc.title == "The Transformer Architecture Explained"
    assert doc.source_type == "web"
    assert doc.source_url == "https://example.com/article"
    assert doc.upload_date == "2024-03-15"
    assert doc.metadata["author"] == "Jane Doe"
    assert doc.metadata["site"] == "example.com"


def test_web_extract_includes_body():
    with patch("any2md.handlers.web._fetch_and_extract", return_value=_FAKE_RESULT):
        doc = WebHandler().extract("https://example.com/article")

    assert "Transformer" in doc.body_markdown


def test_web_extract_handles_empty_result():
    with patch("any2md.handlers.web._fetch_and_extract", return_value={}):
        doc = WebHandler().extract("https://example.com/article")

    assert doc.title  # should not be empty
    assert doc.source_type == "web"


def test_clean_title_strips_site_suffix_matching_sitename():
    from any2md.handlers.web import _clean_title

    assert _clean_title("Why Sleep Matters | LifeScience", "LifeScience") == "Why Sleep Matters"


def test_clean_title_strips_dash_branding_without_sitename():
    from any2md.handlers.web import _clean_title

    assert _clean_title("Why Sleep Matters - LifeScience News", None) == "Why Sleep Matters"


def test_clean_title_keeps_plain_title():
    from any2md.handlers.web import _clean_title

    assert _clean_title("Why Sleep Matters", "LifeScience") == "Why Sleep Matters"


def test_web_falls_back_to_html_title_when_trafilatura_has_none():
    result = {
        "text": "A long enough body of article text to be a real note about sleep science.",
        "title": None,
        "sitename": "LifeScience",
        "html": "<head><title>Real Headline | LifeScience</title></head><body>x</body>",
    }
    with patch("any2md.handlers.web._fetch_and_extract", return_value=result):
        doc = WebHandler().extract("https://www.lifescience.net/x")
    assert doc.title == "Real Headline"


def test_web_falls_back_to_h1_when_no_title_tag():
    result = {
        "text": "body text long enough to matter here and there",
        "title": None,
        "sitename": None,
        "html": "<body><h1>The H1 Headline</h1><p>x</p></body>",
    }
    with patch("any2md.handlers.web._fetch_and_extract", return_value=result):
        doc = WebHandler().extract("https://x.com/a")
    assert doc.title == "The H1 Headline"
