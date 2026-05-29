"""URL canonicalization — strip tracking params, keep functional ones, drop fragment."""

import pytest

from any2md.url import canonical_url


def test_strips_utm_and_ad_tracking_params():
    url = "https://www.bcg.com/pub/x?utm_source=search&utm_medium=cpc&gad_source=1&gclsrc=aw.ds"
    assert canonical_url(url) == "https://www.bcg.com/pub/x"


def test_keeps_youtube_video_id_drops_share_tracking():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&si=AbC123"
    assert canonical_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_keeps_functional_params_like_stackoverflow_answertab():
    url = "https://stackoverflow.com/questions/11227809/title?answertab=votes"
    assert canonical_url(url) == url


def test_drops_fragment():
    assert canonical_url("https://x.com/a/b#section-3") == "https://x.com/a/b"


def test_lowercases_scheme_and_host_only():
    # Path and query-key case are preserved; only scheme + host are lowercased.
    assert (
        canonical_url("HTTPS://Example.COM/Path/Page?Q=Value")
        == "https://example.com/Path/Page?Q=Value"
    )


def test_preserves_order_of_kept_params():
    url = "https://x.com/a?a=1&utm_campaign=z&b=2&fbclid=xyz&c=3"
    assert canonical_url(url) == "https://x.com/a?a=1&b=2&c=3"


def test_non_http_returned_unchanged():
    assert canonical_url("/Users/me/file.pdf") == "/Users/me/file.pdf"
    assert canonical_url("ftp://host/x") == "ftp://host/x"


def test_no_query_left_drops_question_mark():
    assert canonical_url("https://x.com/a?utm_source=foo") == "https://x.com/a"


@pytest.mark.parametrize(
    "tracker",
    [
        "gclid=abc",
        "fbclid=abc",
        "gbraid=abc",
        "wbraid=abc",
        "mc_eid=abc",
        "igshid=abc",
        "msclkid=abc",
        "ref=twitter",
    ],
)
def test_common_trackers_stripped(tracker):
    assert canonical_url(f"https://x.com/a?{tracker}") == "https://x.com/a"
