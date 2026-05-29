import pytest

from any2md.enrich.base import Summarizer
from any2md.enrich.enricher import enrich
from any2md.enrich.extractive import ExtractiveSummarizer
from any2md.enrich.providers import get_summarizer
from any2md.models import Document
from any2md.render import render


class FakeSummarizer(Summarizer):
    def summarize(self, title: str, body: str) -> dict:
        return {
            "summary": "A short summary.",
            "tags": ["ai", "ml"],
            "wikilinks": ["Neural Net", "Backprop"],
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


def test_enrich_fills_fields_from_summarizer():
    doc = _doc()
    enrich(doc, FakeSummarizer())
    assert doc.summary == "A short summary."
    assert doc.tags == ["ai", "ml"]
    assert doc.wikilinks == ["Neural Net", "Backprop"]


def test_enriched_fields_appear_in_rendered_markdown():
    doc = _doc()
    enrich(doc, FakeSummarizer())
    out = render(doc)
    assert "> **Summary:** A short summary." in out
    assert "tags: [ai, ml]" in out
    assert "[[Neural Net]], [[Backprop]]" in out


def test_summarizer_none_leaves_doc_unchanged():
    doc = _doc()
    enrich(doc, None)
    assert doc.summary is None
    assert doc.tags == []
    assert doc.wikilinks == []


def test_enrich_swallows_summarizer_errors():
    class Boom(Summarizer):
        def summarize(self, title: str, body: str) -> dict:
            raise RuntimeError("model down")

    doc = _doc()
    enrich(doc, Boom())  # must not raise
    assert doc.summary is None


def test_extractive_produces_summary_tags_wikilinks():
    body = (
        "Transformers use self-attention. Self-attention lets models weigh tokens. "
        "Attention replaced recurrence in many NLP tasks. The Transformer architecture "
        "scales well. Attention is computed with queries keys and values."
    )
    out = ExtractiveSummarizer().summarize("Transformers", body)
    assert out["summary"]
    assert len(out["tags"]) > 0
    assert isinstance(out["wikilinks"], list)


def test_extractive_empty_body_is_safe():
    out = ExtractiveSummarizer().summarize("X", "")
    assert out["summary"] == ""
    assert out["tags"] == []
    assert out["wikilinks"] == []


def test_extractive_wikilinks_drop_bare_stopwords():
    # Capitalized stopword + lowercase word (sentence starts) must NOT yield "[[The]]"/"[[This]]".
    body = (
        "The retriever fetches documents. This grounds the model. "
        "The retriever uses embeddings. This reduces hallucination. "
        "Vector Search powers retrieval. Vector Search is fast."
    )
    links = ExtractiveSummarizer().summarize("X", body)["wikilinks"]
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


def test_get_summarizer_none_returns_none():
    assert get_summarizer("none") is None


def test_get_summarizer_extractive_is_default_capable():
    assert isinstance(get_summarizer("extractive"), Summarizer)


def test_get_summarizer_ollama_constructs_without_network():
    assert isinstance(get_summarizer("ollama"), Summarizer)


def test_get_summarizer_rejects_removed_api_providers():
    with pytest.raises(ValueError):
        get_summarizer("groq")
