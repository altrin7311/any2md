"""Pure-Python extractive summarizer. No model, no network, no deps — works everywhere.

TextRank-style: clean the markdown down to prose, rank sentences with a PageRank over a
sentence-similarity graph, blend in a lead bias + title overlap, then select with greedy
MMR so the summary isn't redundant. Tags = distinctive content words (title words excluded);
wikilinks = capitalized concept phrases drawn from the cleaned prose (not tables/nav).
"""

import math
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

_MAX_TAGS = 6
_MAX_WIKILINKS = 5
_DAMPING = 0.85
_ITERATIONS = 30
_MMR_THRESHOLD = 0.5  # skip a candidate this similar to an already-picked sentence
_TLDR_MAX = 3  # the TL;DR is always a mini 1-3 sentence lead, independent of source length

# Generic descriptors / academic filler that score high on frequency but carry no topic signal.
# Tags drawn from these read as noise ("based", "best", "dominant") — drop them.
_GENERIC = {
    "based",
    "best",
    "good",
    "better",
    "great",
    "various",
    "important",
    "recent",
    "current",
    "similar",
    "different",
    "possible",
    "available",
    "certain",
    "particular",
    "common",
    "major",
    "minor",
    "simple",
    "complex",
    "dominant",
    "several",
    "multiple",
    "single",
    "many",
    "much",
    "more",
    "most",
    "less",
    "using",
    "used",
    "make",
    "made",
    "show",
    "shows",
    "shown",
    "propose",
    "proposed",
    "present",
    "presented",
    "result",
    "results",
    "including",
    "include",
    "includes",
    "also",
    "however",
    "therefore",
    "thus",
    "while",
    "between",
    "through",
    "across",
    "within",
    "without",
    "because",
    "since",
    "able",
    "need",
    "needs",
    "new",
    "old",
    "first",
    "second",
    "large",
    "small",
    "high",
    "long",
    "short",
    "full",
    "early",
    "late",
    "given",
    "each",
    "other",
    "another",
    "both",
    "every",
    "upon",
    "over",
    "under",
    "above",
    "below",
    "previously",
    "reported",
    "significantly",
    "entirely",
    "substantially",
    "primary",
    "superior",
    "performing",
}

# Capitalized proper nouns that aren't topics: languages, months, days, paper scaffolding.
_COMMON_PROPER = {
    "english",
    "german",
    "french",
    "spanish",
    "italian",
    "portuguese",
    "dutch",
    "russian",
    "chinese",
    "japanese",
    "korean",
    "arabic",
    "hindi",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "figure",
    "table",
    "section",
    "appendix",
    "equation",
    "chapter",
    "abstract",
}

# Sentences with these cues state the contribution/thesis — boost them so the TL;DR leads with the
# point, not the background. Harmless on prose that has no such cue.
_THESIS_CUES = (
    "we propose",
    "we present",
    "we introduce",
    "we show",
    "we describe",
    "we demonstrate",
    "we find",
    "this paper",
    "in this work",
    "in this paper",
    "our model",
    "our approach",
    "the key idea",
    "the main",
    "in short",
    "in summary",
)

# Lines that are structure/boilerplate, not prose — dropped before summarizing.
_LIST_MARKER = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
_BOILERPLATE = re.compile(
    r"(copyright|all rights reserved|page\s+\d+\s+of\s+\d+|^\s*navigation\s*:)", re.I
)
_URL = re.compile(r"https?://\S+")


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z'-]+", text.lower())


def _content(text: str) -> list[str]:
    return [w for w in _words(text) if w not in _STOPWORDS and len(w) > 2]


def _clean_prose(body: str) -> str:
    """Strip markdown structure (tables, headings, lists, code, nav, boilerplate, URLs)
    so sentence extraction sees prose, not scaffolding."""
    kept: list[str] = []
    in_code = False
    for raw in body.splitlines():
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s:
            continue
        if s.startswith(("|", "#", ">")):  # table row / heading / blockquote
            continue
        if _LIST_MARKER.match(s):  # bullet / numbered item
            continue
        if s.count("|") >= 2:  # nav bar or inline table
            continue
        if _BOILERPLATE.search(s):
            continue
        kept.append(s)
    text = _URL.sub(" ", " ".join(kept))
    return re.sub(r"\s+", " ", text).strip()


def _split_sentences(text: str) -> list[str]:
    sentences = []
    for part in re.split(r"(?<=[.!?])\s+", text):
        part = part.strip()
        # Real sentences only: enough words, enough content, not a stray fragment.
        if len(_words(part)) >= 5 and len(_content(part)) >= 3 and len(part) > 30:
            sentences.append(part)
    return sentences


def _similarity(a: set[str], b: set[str]) -> float:
    """Classic TextRank overlap, normalized by sentence lengths."""
    if not a or not b:
        return 0.0
    common = len(a & b)
    if not common:
        return 0.0
    denom = math.log(len(a) + 1) + math.log(len(b) + 1)
    return common / denom if denom else 0.0


def _textrank(word_sets: list[set[str]]) -> list[float]:
    n = len(word_sets)
    if n == 1:
        return [1.0]
    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s = _similarity(word_sets[i], word_sets[j])
            sim[i][j] = sim[j][i] = s
    row_sums = [sum(row) or 1e-9 for row in sim]
    scores = [1.0] * n
    for _ in range(_ITERATIONS):
        updated = []
        for i in range(n):
            acc = sum(sim[j][i] / row_sums[j] * scores[j] for j in range(n) if sim[j][i])
            updated.append((1 - _DAMPING) + _DAMPING * acc)
        scores = updated
    return scores


def _select(
    title: str, sentences: list[str], ratio: float, kp_min: int, kp_max: int
) -> tuple[list[str], list[str]]:
    """Distill to a mini TL;DR (<= _TLDR_MAX sentences) plus key points = round(ratio*n) clamped
    into [kp_min, kp_max]. Returns (tldr_sentences, key_point_sentences) in reading order."""
    if not sentences:
        return [], []

    word_sets = [set(_content(s)) for s in sentences]
    ranks = _textrank(word_sets)
    title_words = set(_content(title))
    lead = len(sentences)

    # Blend TextRank with a lead bias (early sentences = topic), title overlap, and a thesis-cue
    # boost so a stated contribution ("we propose …") outranks background throat-clearing.
    final = []
    for i, (rank, ws) in enumerate(zip(ranks, word_sets, strict=True)):
        lead_bonus = 0.15 * (1 - i / lead)
        overlap = len(ws & title_words) / (len(title_words) + 1)
        cue = 0.6 if any(c in sentences[i].lower() for c in _THESIS_CUES) else 0.0
        final.append(rank * (1 + lead_bonus + 0.3 * overlap + cue))

    n = len(sentences)
    n_kp = max(kp_min, min(kp_max, round(ratio * n)))  # key-point budget, clamped per depth level
    n_tldr = min(_TLDR_MAX, n)
    target = n_tldr + n_kp
    order = sorted(range(n), key=lambda i: final[i], reverse=True)

    # Greedy MMR: take highest-scoring non-redundant sentences up to the combined target.
    picked: list[int] = []  # in score order
    for i in order:
        if len(picked) >= target:
            break
        if any(_similarity(word_sets[i], word_sets[p]) > _MMR_THRESHOLD for p in picked):
            continue
        picked.append(i)
    if not picked:
        picked = [order[0]]

    n_tldr = min(n_tldr, len(picked))
    tldr_idx = sorted(picked[:n_tldr])  # highest-scoring → reading order
    kp_idx = sorted(picked[n_tldr:])
    return [sentences[i] for i in tldr_idx], [sentences[i] for i in kp_idx]


def _tags(prose: str, title: str, concepts: list[str]) -> list[str]:
    """Topic tags = the denoised concept phrases first (already proper-noun-ish), then the most
    distinctive content words — minus title words and generic descriptors ("based"/"best")."""
    title_low = title.lower()
    title_words = set(_content(title))
    freq = Counter(
        w for w in _content(prose) if w not in title_words and len(w) >= 4 and w not in _GENERIC
    )

    chosen: list[str] = []

    def _add(tag: str) -> None:
        tag = tag.lower().strip()
        if not tag or tag in title_low:
            return
        if any(tag.startswith(c) or c.startswith(tag) for c in chosen):
            return  # drop near-duplicate stems (cache/caching)
        chosen.append(tag)

    for phrase in concepts:  # topical concepts lead
        if len(chosen) >= _MAX_TAGS:
            break
        _add(phrase)
    for word, _ in freq.most_common():  # then distinctive frequent words
        if len(chosen) >= _MAX_TAGS:
            break
        _add(word)
    return chosen[:_MAX_TAGS]


def _key_phrases(prose: str, title: str) -> list[str]:
    title_low = title.lower()
    # Words capitalized MID-sentence (preceded by a lowercase letter/comma) are real proper
    # nouns; words capitalized only at a sentence start are not. This filters "Latency"/"Read".
    mid_caps = {m.lower() for m in re.findall(r"[a-z0-9,]\s+([A-Z][a-zA-Z0-9]+)", prose)}

    raw = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b", prose)
    cleaned = []
    for phrase in raw:
        words = phrase.split()
        while words and words[0].lower() in _STOPWORDS:  # drop leading "The"/"This"
            words = words[1:]
        if not words:
            continue
        candidate = " ".join(words)
        low = candidate.lower()
        if len(candidate) <= 2 or low in title_low or low in _STOPWORDS:
            continue  # skip fragments, the title itself, bare stopwords
        if low in _COMMON_PROPER:
            continue  # languages / months / "Figure"/"Table" — proper nouns, but not topics
        # A single capitalized word counts only if it's a genuine mid-sentence proper noun.
        if len(words) == 1 and words[0].lower() not in mid_caps:
            continue
        cleaned.append(candidate)
    counts = Counter(cleaned)
    # Prefer multi-word concepts, then frequency.
    ranked = sorted(counts, key=lambda p: (len(p.split()) > 1, counts[p]), reverse=True)
    return ranked[:_MAX_WIKILINKS]


class ExtractiveSummarizer(Summarizer):
    def summarize(
        self, title: str, body: str, *, ratio: float = 0.2, kp_min: int = 3, kp_max: int = 20
    ) -> dict:
        prose = _clean_prose(body)
        if not _content(prose):
            return {"tldr": "", "key_points": [], "tags": [], "concepts": []}
        tldr, key_points = _select(title, _split_sentences(prose), ratio, kp_min, kp_max)
        concepts = _key_phrases(prose, title)
        return {
            "tldr": " ".join(tldr),
            "key_points": key_points,
            "tags": _tags(prose, title, concepts),
            "concepts": concepts,
        }
