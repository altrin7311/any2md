"""Quality tests for the extractive summarizer (TextRank + cleaning + MMR + % depth)."""

from any2md.enrich.extractive import ExtractiveSummarizer

_MESSY = """# Quarterly Engineering Report

| Metric | Q1 | Q2 |
|---|---|---|
| Uptime | 99.1 | 99.7 |

Navigation: Home | Docs | About | Contact

The platform migrated to a new event-driven architecture this quarter. The migration
reduced average request latency by forty percent. Latency reduction was the primary goal
of the rearchitecture.

- bullet one about caching
- bullet two about queues

We also introduced a caching layer backed by Redis. The caching layer cut database load
substantially. Database load dropped because most reads now hit the cache. Engineers
reported the new system is easier to operate.

Copyright 2026 Acme Corp. All rights reserved. Page 1 of 12.

Read more at https://example.com/report for the full breakdown.
"""


_ABSTRACT = (
    "The dominant sequence transduction models are based on complex recurrent or convolutional "
    "neural networks in an encoder-decoder configuration. The best performing models also connect "
    "the encoder and decoder through an attention mechanism. We propose a new simple network "
    "architecture, the Transformer, based solely on attention mechanisms, dispensing with "
    "recurrence and convolutions entirely. Experiments on two machine translation tasks show these "
    "models to be superior in quality while being more parallelizable and requiring significantly "
    "less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German "
    "translation task, improving over the best previously reported results."
)


def _summ(title, body, ratio=0.2):
    return ExtractiveSummarizer().summarize(title, body, ratio=ratio)


def test_tldr_leads_with_contribution_not_throat_clearing():
    # The thesis ("we propose ... the Transformer") must surface in the TL;DR, not stay buried
    # behind the background first sentence ("The dominant ... models are based on ...").
    out = _summ("Attention Is All You Need", _ABSTRACT, ratio=0.3)
    low = out["tldr"].lower()
    assert "transformer" in low or "propose" in low


def test_tags_drop_generic_descriptor_words():
    out = _summ("Attention Is All You Need", _ABSTRACT, ratio=0.3)
    for junk in ("based", "best", "dominant", "previously", "reported"):
        assert junk not in out["tags"]


def test_tags_surface_real_topics():
    out = _summ("Attention Is All You Need", _ABSTRACT, ratio=0.3)
    assert any(t in out["tags"] for t in ("transformer", "attention"))


def test_concepts_drop_language_names():
    out = _summ("Attention Is All You Need", _ABSTRACT, ratio=0.3)
    assert "English" not in out["concepts"]
    assert "German" not in out["concepts"]


def _text(out):
    """All distilled prose: TL;DR plus every key point."""
    return (out["tldr"] + " " + " ".join(out["key_points"])).lower()


def test_returns_new_contract_keys():
    out = _summ("Quarterly Engineering Report", _MESSY)
    assert set(out) == {"tldr", "key_points", "tags", "concepts"}
    assert isinstance(out["tldr"], str)
    assert isinstance(out["key_points"], list)


def test_drops_list_and_table_artifacts():
    out = _summ("Quarterly Engineering Report", _MESSY, ratio=0.35)
    assert "bullet one" not in _text(out)
    assert "bullet" not in out["tags"]


def test_concepts_drop_table_nav_and_title():
    out = _summ("Quarterly Engineering Report", _MESSY, ratio=0.35)
    links = out["concepts"]
    assert "Metric" not in links and "Uptime" not in links  # table headers
    assert "Navigation" not in links and "Home" not in links  # nav bar
    assert "Quarterly Engineering Report" not in links  # the title itself


def test_tags_exclude_title_words_and_generic_noise():
    out = _summ("Quarterly Engineering Report", _MESSY)
    assert "report" not in out["tags"]  # a title word
    assert "new" not in out["tags"]  # too generic / short


def test_captures_the_thesis():
    out = _summ("Quarterly Engineering Report", _MESSY, ratio=0.35)
    low = _text(out)
    assert "architecture" in low or "latency" in low


def test_tldr_and_key_points_are_disjoint():
    out = _summ("Quarterly Engineering Report", _MESSY, ratio=0.35)
    for kp in out["key_points"]:
        assert kp not in out["tldr"]  # the TL;DR sentences aren't repeated as bullets


def test_higher_depth_keeps_more_content():
    low = _summ("Quarterly Engineering Report", _MESSY, ratio=0.10)
    high = _summ("Quarterly Engineering Report", _MESSY, ratio=0.35)
    low_words = len(_text(low).split())
    high_words = len(_text(high).split())
    assert high_words >= low_words


def test_not_redundant():
    body = (
        "The cache speeds up reads dramatically. " * 4
        + "Separately, the new queue smooths traffic spikes during peak load hours. "
        + "Observability improved with structured tracing across every service boundary."
    )
    out = _summ("Caching", body, ratio=0.35)
    assert _text(out).count("the cache speeds up reads dramatically") <= 1


def test_empty_body_is_safe():
    out = _summ("X", "")
    assert out["tldr"] == ""
    assert out["key_points"] == []
    assert out["tags"] == []
    assert out["concepts"] == []
