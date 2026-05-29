"""Pure-Python extractive summarizer. No model, no network, no deps — works everywhere.

Frequency-based (Luhn-style): score sentences by the frequency of their content words,
keep the top few in original order. Tags = most frequent content words. Wikilinks =
most frequent capitalized phrases (proper-noun-ish concepts).
"""

import re
from collections import Counter

from any2md.enrich.base import Summarizer

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "as",
    "by",
    "at",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "they",
    "them",
    "their",
    "we",
    "you",
    "he",
    "she",
    "his",
    "her",
    "i",
    "not",
    "no",
    "can",
    "will",
    "would",
    "should",
    "could",
    "has",
    "have",
    "had",
    "do",
    "does",
    "did",
    "so",
    "than",
    "then",
    "there",
    "here",
    "which",
    "who",
    "what",
    "when",
    "where",
    "how",
    "all",
    "any",
    "into",
    "out",
    "up",
    "down",
    "over",
    "more",
    "most",
    "some",
    "such",
    "only",
    "also",
    "about",
    # spoken-filler + contractions: auto-caption transcripts are full of these, and
    # frequency scoring otherwise surfaces them as "key" words. They carry no meaning.
    "just",
    "like",
    "really",
    "basically",
    "actually",
    "okay",
    "ok",
    "yeah",
    "right",
    "now",
    "know",
    "mean",
    "going",
    "gonna",
    "wanna",
    "kind",
    "sort",
    "stuff",
    "thing",
    "things",
    "lot",
    "get",
    "got",
    "make",
    "want",
    "use",
    "see",
    "go",
    "one",
    "two",
    "let",
    "lets",
    "im",
    "ive",
    "dont",
    "thats",
    "we're",
    "it's",
    "that's",
    "i'm",
    "don't",
    "you're",
    "let's",
    "we'll",
    "i'll",
    "there's",
    "here's",
}

_SUMMARY_SENTENCES = 3
_MAX_TAGS = 6
_MAX_WIKILINKS = 5


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z'-]+", text.lower())


def _sentences(text: str) -> list[str]:
    # Drop markdown table rows / headings, then split on sentence terminators.
    cleaned = "\n".join(
        ln for ln in text.splitlines() if not ln.lstrip().startswith(("|", "#", ">"))
    )
    parts = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    return [s.strip() for s in parts if len(s.strip()) > 20]


def _key_phrases(text: str) -> list[str]:
    raw = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b", text)
    cleaned = []
    for phrase in raw:
        words = phrase.split()
        # Drop leading capitalized stopwords: bare "The"/"This" → empty (dropped);
        # "The Transformer" → "Transformer".
        while words and words[0].lower() in _STOPWORDS:
            words = words[1:]
        if not words:
            continue
        candidate = " ".join(words)
        if len(candidate) > 2:
            cleaned.append(candidate)
    counts = Counter(cleaned)
    return [p for p, _ in counts.most_common(_MAX_WIKILINKS)]


class ExtractiveSummarizer(Summarizer):
    def summarize(self, title: str, body: str) -> dict:
        content = [w for w in _words(body) if w not in _STOPWORDS and len(w) > 2]
        if not content:
            return {"summary": "", "tags": [], "wikilinks": []}

        freq = Counter(content)
        sentences = _sentences(body)

        scored = []
        for index, sentence in enumerate(sentences):
            sw = [w for w in _words(sentence) if w in freq]
            score = sum(freq[w] for w in sw) / (len(sw) + 1)
            scored.append((score, index, sentence))

        top = sorted(scored, reverse=True)[:_SUMMARY_SENTENCES]
        summary = " ".join(s for _, _, s in sorted(top, key=lambda t: t[1]))

        tags = [w for w, _ in freq.most_common(_MAX_TAGS)]
        return {"summary": summary, "tags": tags, "wikilinks": _key_phrases(body)}
