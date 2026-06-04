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


def _varied_body(n):
    """n distinct, low-overlap sentences so MMR keeps them (depth math is what we test).

    Uses random 6-letter words (all > 2 chars so none are dropped as too-short content words),
    drawn from a large pool so any two sentences share almost nothing → no MMR dedup collapse.
    """
    import random

    rng = random.Random(1)
    vocab: list[str] = []
    seen: set[str] = set()
    while len(vocab) < 80:
        word = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6))
        if word not in seen:
            seen.add(word)
            vocab.append(word)
    out = []
    for _ in range(n):
        words = rng.sample(vocab, 8)
        words[0] = words[0].capitalize()
        out.append(" ".join(words) + ".")
    return " ".join(out)


def test_depth_is_monotonic_and_bounded_and_tldr_is_mini():
    import re

    from any2md import depth

    s = ExtractiveSummarizer()
    body = _varied_body(120)  # long source so caps bite
    counts = {}
    for level in ("low", "medium", "high"):
        lo, hi = depth.bounds(level)
        out = s.summarize(
            "Governing Principles", body, ratio=depth.ratio(level), kp_min=lo, kp_max=hi
        )
        counts[level] = len(out["key_points"])
        tldr_sents = [x for x in re.split(r"(?<=[.!?])\s+", out["tldr"].strip()) if x]
        assert len(tldr_sents) <= 3  # TL;DR stays mini regardless of source length

    assert counts["low"] < counts["medium"] < counts["high"]  # depth visibly changes output
    assert counts["low"] <= 6  # low stays a tight digest
    assert counts["high"] >= 30  # high keeps most of the source, not a truncated handful


def test_html_and_bylines_and_emails_do_not_leak():
    body = (
        '<a href="https://x.com"><img src="logo.png"></a> '
        "Focus on building applications, not infrastructure, with this framework. "
        "**nefele** I saw your demo at the conference and it looked great overall. "
        "AshishVaswani noam@google.com NikiParmar affiliations listed here. "
        "Figure 3 shows the attention heatmap across layers in detail. "
        "The framework provides automatic validation and serialization for requests."
    )
    out = ExtractiveSummarizer().summarize(
        "Framework Overview", body, ratio=0.5, kp_min=3, kp_max=20
    )
    blob = out["tldr"] + " " + " ".join(out["key_points"]) + " " + " ".join(out["tags"])
    assert "<" not in blob and ">" not in blob  # no HTML tags/attributes
    assert "**" not in blob  # no markdown bold bylines
    assert "nefele" not in blob  # the byline word itself is gone
    assert "@google.com" not in blob and "noam" not in blob  # author/email block dropped
    assert "Figure 3" not in blob  # figure caption dropped


def test_keyphrases_drop_camelcase_authors_and_do_not_merge_across_sentences():
    from any2md.enrich.extractive import _key_phrases

    prose = "We used Multi Head Attention. Generators are lazy. Iterables come first."
    phrases = _key_phrases(prose, "Title")
    assert "AshishVaswani" not in phrases
    assert all(" When" not in p and "Iterables Generators" not in p for p in phrases)


def test_deglue_splits_long_runon_tokens_only():
    from any2md.enrich.extractive import _deglue

    assert "BLEU" in _deglue("ourmodelachievesanewBLEUscoreofManyThings")
    assert _deglue("GitHub") == "GitHub"  # short legit CamelCase untouched


def test_tags_drop_singletons_and_nonalpha():
    from any2md.enrich.extractive import _tags

    prose = "transformer transformer attention attention attention wmt2014 gpus."
    tags = _tags(prose, "Title", [])
    assert "attention" in tags
    assert "wmt2014" not in tags  # non-alpha dropped
