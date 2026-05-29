"""Canonicalize URLs so the vault stores clean links and dedup works across tracking variants.

Strips analytics/ad tracking query params (and the fragment), keeps every functional param,
lowercases only the scheme + host. Non-http(s) inputs (local paths, ftp) pass through untouched.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query keys that are pure tracking — safe to drop everywhere.
_TRACKING_KEYS = {
    "gclid",
    "gclsrc",
    "dclid",
    "gbraid",
    "wbraid",
    "fbclid",
    "msclkid",
    "yclid",
    "mc_eid",
    "mc_cid",
    "mkt_tok",
    "_hsenc",
    "_hsmi",
    "igshid",
    "igsh",
    "vero_id",
    "oly_anon_id",
    "oly_enc_id",
    "si",  # youtube / spotify share-tracking (not the video id)
    "ref",
    "ref_src",
    "ref_url",
}
# Keys with these prefixes are tracking families (utm_*, gad_source/gad_campaignid, ...).
_TRACKING_PREFIXES = ("utm_", "gad_")


def _is_tracking(key: str) -> bool:
    low = key.lower()
    return low in _TRACKING_KEYS or low.startswith(_TRACKING_PREFIXES)


def canonical_url(url: str) -> str:
    """Return the URL with tracking params + fragment removed and scheme/host lowercased.
    Functional params (youtube ?v=, SO ?answertab=) and their order are preserved.
    Non-http(s) inputs are returned unchanged."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https"):
        return url

    kept = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)
    ]
    query = urlencode(kept)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))
