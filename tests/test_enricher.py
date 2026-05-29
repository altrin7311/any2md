import pytest

from any2md.enrich.base import Summarizer
from any2md.enrich.enricher import enrich, inline_links, normalize_tag
from any2md.enrich.extractive import ExtractiveSummarizer
from any2md.enrich.providers import get_summarizer
from any2md.models import Document
from any2md.render import render


def test_inline_links_wraps_first_occurrence():
    out = inline_links("The Transformer uses attention", ["Transformer"])
    assert out == "The [[Transformer]] uses attention"


def test_inline_links_is_case_insensitive_but_keeps_text_casing():
    out = inline_links("The Transformer model", ["transformer"])
    assert out == "The [[Transformer]] model"


def test_inline_links_only_first_occurrence():
    out = inline_links("Transformer then Transformer", ["Transformer"])
    assert out == "[[Transformer]] then Transformer"


def test_inline_links_whole_word_only():
    out = inline_links("a smart artist", ["art"])
    assert out == "a smart artist"  # not inside 'smart'/'artist'


def test_inline_links_skips_already_linked():
    out = inline_links("[[Transformer]] rocks and Transformer again", ["Transformer"])
    # the existing link stays; we don't double-wrap, and we don't touch the bracketed one
    assert out.count("[[Transformer]]") == 2  # the original + the next bare occurrence wrapped


def test_inline_links_phrase_absent_is_noop():
    assert inline_links("nothing here", ["Missing"]) == "nothing here"


def test_inline_links_multiple_phrases():
    out = inline_links("Self-Attention powers the Transformer", ["Transformer", "Self-Attention"])
    assert "[[Transformer]]" in out
    assert "[[Self-Attention]]" in out


class FakeSummarizer(Summarizer):
    def summarize(self, title: str, body: str, *, ratio: float = 0.2) -> dict:
        return {
            "tldr": "Neural Net basics in one line.",
            "key_points": ["Backprop trains the Neural Net", "Gradients flow backward"],
            "tags": ["ai", "ml"],
            "concepts": ["Neural Net", "Backprop"],
        }


def _doc(body: str = "Some content about neural nets.") -> Document:
    return Document(
        title="T",
        source_url=None,
        source_type="pdf",
        upload_date=None,
        extraction_date="2026-05-28",
        body_markdown=body,
        metadata={},
    )


def test_enrich_fills_fields_and_inlines_links():
    doc = _doc()
    enrich(doc, FakeSummarizer())
    assert doc.summary == "[[Neural Net]] basics in one line."  # tldr, links inlined
    assert doc.key_points == ["[[Backprop]] trains the [[Neural Net]]", "Gradients flow backward"]
    assert doc.tags == ["ai", "ml"]
    assert doc.wikilinks == ["Neural Net", "Backprop"]  # raw concepts kept (not rendered as list)


def test_enriched_fields_appear_in_rendered_markdown():
    doc = _doc()
    enrich(doc, FakeSummarizer())
    out = render(doc)
    assert "> [!summary] TL;DR" in out
    assert "[[Neural Net]] basics in one line." in out
    assert "## Key Points" in out
    assert "- [[Backprop]] trains the [[Neural Net]]" in out
    assert "tags: [ai, ml]" in out


def test_summarizer_none_leaves_doc_unchanged():
    doc = _doc()
    enrich(doc, None)
    assert doc.summary is None
    assert doc.key_points == []
    assert doc.tags == []
    assert doc.wikilinks == []


def test_enrich_swallows_summarizer_errors():
    class Boom(Summarizer):
        def summarize(self, title: str, body: str, *, ratio: float = 0.2) -> dict:
            raise RuntimeError("model down")

    doc = _doc()
    enrich(doc, Boom())  # must not raise
    assert doc.summary is None


class _Boom(Summarizer):
    def summarize(self, title: str, body: str, *, ratio: float = 0.2) -> dict:
        raise RuntimeError("model down")


def test_enrich_returns_true_on_success():
    assert enrich(_doc(), FakeSummarizer()) is True


def test_enrich_returns_true_for_none_summarizer():
    assert enrich(_doc(), None) is True


def test_enrich_returns_false_when_summarizer_raises():
    assert enrich(_doc(), _Boom()) is False


def test_enrich_with_fallback_ollama_down_uses_extractive(monkeypatch):
    from any2md.enrich import enricher

    monkeypatch.setattr(
        enricher,
        "get_summarizer",
        lambda name: _Boom() if name == "ollama" else FakeSummarizer(),
    )
    doc = _doc()
    enricher.enrich_with_fallback(doc, "ollama")
    assert "basics in one line" in doc.summary  # extractive (Fake) filled it after ollama failed
    assert any("ollama unreachable" in w for w in doc.warnings)


def test_enrich_with_fallback_success_no_warning(monkeypatch):
    from any2md.enrich import enricher

    monkeypatch.setattr(enricher, "get_summarizer", lambda name: FakeSummarizer())
    doc = _doc()
    enricher.enrich_with_fallback(doc, "ollama")
    assert "basics in one line" in doc.summary
    assert doc.warnings == []


def test_enrich_with_fallback_non_ollama_failure_does_not_fall_back(monkeypatch):
    from any2md.enrich import enricher

    monkeypatch.setattr(enricher, "get_summarizer", lambda name: _Boom())
    doc = _doc()
    enricher.enrich_with_fallback(doc, "extractive")
    assert doc.summary is None
    assert doc.warnings == []


def test_extractive_produces_tldr_tags_concepts():
    body = (
        "Transformers use self-attention. Self-attention lets models weigh tokens. "
        "Attention replaced recurrence in many NLP tasks. The Transformer architecture "
        "scales well. Attention is computed with queries keys and values."
    )
    out = ExtractiveSummarizer().summarize("Transformers", body)
    assert out["tldr"] or out["key_points"]
    assert len(out["tags"]) > 0
    assert isinstance(out["concepts"], list)


def test_extractive_empty_body_is_safe():
    out = ExtractiveSummarizer().summarize("X", "")
    assert out["tldr"] == ""
    assert out["key_points"] == []
    assert out["tags"] == []
    assert out["concepts"] == []


def test_extractive_concepts_drop_bare_stopwords():
    # Capitalized stopword + lowercase word (sentence starts) must NOT yield "[[The]]"/"[[This]]".
    body = (
        "The retriever fetches documents. This grounds the model. "
        "The retriever uses embeddings. This reduces hallucination. "
        "Vector Search powers retrieval. Vector Search is fast."
    )
    links = ExtractiveSummarizer().summarize("X", body)["concepts"]
    assert "The" not in links
    assert "This" not in links


def test_extractive_drops_spoken_filler_from_tags():
    # Auto-caption speech is full of fillers; tags should surface content, not "gonna"/"like".
    body = (
        "so we're gonna like just basically build a transformer right now you know "
        "i mean it's gonna be really cool okay so the transformer uses attention "
        "attention attention and the transformer model the transformer architecture "
        "really matters for language modeling and tokens and embeddings."
    )
    tags = ExtractiveSummarizer().summarize("X", body)["tags"]
    for filler in ("gonna", "like", "just", "basically", "really", "okay", "know"):
        assert filler not in tags
    assert "transformer" in tags  # actual content word survives


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Artificial Intelligence", "artificial-intelligence"),
        ("Machine_Learning", "machine-learning"),
        ("NLP", "nlp"),
        ("  Deep   Learning  ", "deep-learning"),
        ("C++", "c"),
        ("   ", ""),
    ],
)
def test_normalize_tag(raw, expected):
    assert normalize_tag(raw) == expected


class _SpacedTagSummarizer(Summarizer):
    def summarize(self, title: str, body: str, *, ratio: float = 0.2) -> dict:
        # Ollama happily returns multiword, mixed-case, and duplicate tags — all invalid/messy
        # as Obsidian tags (which cannot contain spaces).
        return {
            "tldr": "x",
            "key_points": [],
            "concepts": [],
            "tags": ["Artificial Intelligence", "NLP", "nlp", "   "],
        }


def test_enrich_normalizes_and_dedupes_tags():
    doc = _doc()
    enrich(doc, _SpacedTagSummarizer())
    assert doc.tags == ["artificial-intelligence", "nlp"]  # valid, deduped, empties dropped


def test_get_summarizer_none_returns_none():
    assert get_summarizer("none") is None


def test_get_summarizer_extractive_is_default_capable():
    assert isinstance(get_summarizer("extractive"), Summarizer)


def test_get_summarizer_ollama_constructs_without_network():
    assert isinstance(get_summarizer("ollama"), Summarizer)


def test_get_summarizer_rejects_removed_api_providers():
    with pytest.raises(ValueError):
        get_summarizer("groq")
