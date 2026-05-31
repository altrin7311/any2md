# Quality + Robustness Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/depth` actually change summary length, stop HTML/boilerplate/byline leakage into summaries, and make handlers degrade gracefully (GitHub redirects, dead sources, Reddit, YouTube).

**Architecture:** Four workstreams. WS1 rewrites the depth math (`depth.py` + `extractive._select`) and threads per-level key-point caps through the summarizer. WS2 hardens `extractive._clean_prose` / `_key_phrases` / `_tags`. WS3 adds GitHub redirect-following + a central HTTP-error → clean-skip in the pipeline + a docx test. WS4 makes Reddit (old.reddit retry) and YouTube (deno JS runtime) more robust.

**Tech Stack:** Python 3.11, httpx, markitdown, yt-dlp, pytest. No new dependencies.

**Branch:** `usability-fixes` (build after the usability plan; this plan reuses `any2md/errors.py:SourceUnavailable` and the pipeline try/except introduced there).

---

## File Structure

- Modify: `any2md/depth.py` — new ratio table (10/20/35) + per-level key-point `BOUNDS`.
- Modify: `any2md/enrich/extractive.py` — `_select` clamp + fixed TL;DR; HTML/byline/boilerplate stripping; `_key_phrases` + `_tags` denoise.
- Modify: `any2md/enrich/base.py` — `summarize` gains `kp_min`/`kp_max`.
- Modify: `any2md/enrich/ollama.py` — `summarize` accepts (ignores) `kp_min`/`kp_max`.
- Modify: `any2md/enrich/enricher.py` — thread `kp_min`/`kp_max`; accurate fallback message.
- Modify: `any2md/pipeline.py` — pass per-level bounds; catch `httpx.HTTPStatusError` → clean skip.
- Modify: `any2md/handlers/github.py` — `follow_redirects=True` on all fetches.
- Modify: `any2md/handlers/reddit.py` — old.reddit retry + `SourceUnavailable` on total failure.
- Modify: `any2md/handlers/youtube.py` — JS-runtime detection + clearer no-caption warning.
- Modify: `Dockerfile` — install `deno` (yt-dlp's default JS runtime).
- Tests: `tests/test_depth.py`, `tests/test_extractive_quality.py`, `tests/test_github.py`, `tests/test_pipeline.py`, `tests/test_reddit.py`, `tests/test_youtube.py`, `tests/test_files_handler.py`.

---

## WS1 — Depth distillation

### Task 1: New depth table + bounds

**Files:**
- Modify: `any2md/depth.py:7-12`
- Test: `tests/test_depth.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_depth.py`:

```python
def test_ratios_match_docs_and_bounds_are_tiered():
    from any2md import depth

    assert depth.ratio("low") == 0.10
    assert depth.ratio("medium") == 0.20
    assert depth.ratio("high") == 0.35
    assert depth.bounds("low") == (3, 6)
    assert depth.bounds("medium") == (6, 12)
    assert depth.bounds("high") == (10, 20)
    assert depth.bounds("anything-unknown") == (6, 12)  # defaults to medium
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/pytest tests/test_depth.py::test_ratios_match_docs_and_bounds_are_tiered -v`
Expected: FAIL — `ratio("medium")` is `0.30`, and `bounds` does not exist.

- [ ] **Step 3: Update `depth.py`**

In `any2md/depth.py`, replace the `RATIOS` line and add `BOUNDS` + a `bounds()` function. The top of the file becomes:

```python
LEVELS = ["low", "medium", "high", "raw"]
RATIOS = {"low": 0.10, "medium": 0.20, "high": 0.35}
# Per-level key-point budget (min, max). The chosen count is the ratio of the source clamped
# into this band, so levels never collapse together and never explode on long sources.
BOUNDS = {"low": (3, 6), "medium": (6, 12), "high": (10, 20)}


def ratio(level: str) -> float:
    return RATIOS.get(level, RATIOS["medium"])


def bounds(level: str) -> tuple[int, int]:
    return BOUNDS.get(level, BOUNDS["medium"])
```

(Leave `is_raw`, `next_level`, `prev_level` unchanged below.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_depth.py::test_ratios_match_docs_and_bounds_are_tiered -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add any2md/depth.py tests/test_depth.py
git commit -m "feat: depth ratios 10/20/35 + per-level key-point bounds"
```

### Task 2: Rewrite `_select` (clamp + fixed TL;DR) and thread bounds

**Files:**
- Modify: `any2md/enrich/extractive.py` (`_select` ~393-431, `summarize` ~494-506, add `_TLDR_MAX`)
- Modify: `any2md/enrich/base.py`
- Modify: `any2md/enrich/ollama.py:42`
- Modify: `any2md/enrich/enricher.py`
- Modify: `any2md/pipeline.py:7,44`
- Test: `tests/test_extractive_quality.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_extractive_quality.py`:

```python
def _varied_body(n):
    """n distinct, low-overlap prose sentences so MMR keeps them (depth math is what we test)."""
    import random

    vocab = (
        "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron "
        "pi rho sigma tau upsilon phi chi psi omega quanta vector tensor manifold gradient "
        "entropy kernel lattice spectrum cipher photon quark boson lepton hadron plasma"
    ).split()
    rng = random.Random(0)
    out = []
    for _ in range(n):
        out.append("The " + " ".join(rng.sample(vocab, 8)) + " principle clearly governs everything.")
    return " ".join(out)


def test_depth_is_monotonic_and_bounded_and_tldr_is_mini():
    import re

    from any2md import depth
    from any2md.enrich.extractive import ExtractiveSummarizer

    s = ExtractiveSummarizer()
    body = _varied_body(120)  # long source so caps bite
    counts = {}
    for level in ("low", "medium", "high"):
        lo, hi = depth.bounds(level)
        out = s.summarize("Governing Principles", body, ratio=depth.ratio(level), kp_min=lo, kp_max=hi)
        counts[level] = len(out["key_points"])
        tldr_sents = [x for x in re.split(r"(?<=[.!?])\s+", out["tldr"].strip()) if x]
        assert len(tldr_sents) <= 3  # TL;DR stays mini regardless of source length

    assert counts["low"] < counts["medium"] < counts["high"]  # depth visibly changes output
    assert counts["low"] >= 3 and counts["high"] <= 20  # within the tiered caps
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/pytest tests/test_extractive_quality.py::test_depth_is_monotonic_and_bounded_and_tldr_is_mini -v`
Expected: FAIL — `summarize` has no `kp_min`/`kp_max`, and counts collapse (floor of 8).

- [ ] **Step 3: Update the `Summarizer` ABC**

In `any2md/enrich/base.py`, change the signature:

```python
    @abstractmethod
    def summarize(
        self, title: str, body: str, *, ratio: float = 0.2, kp_min: int = 3, kp_max: int = 20
    ) -> dict:
        """Distill to ~ratio of the source, key points clamped to [kp_min, kp_max]. Return
        {"tldr": str, "key_points": list[str], "tags": list[str], "concepts": list[str]}."""
```

- [ ] **Step 4: Rewrite `_select` and `summarize` in `extractive.py`**

In `any2md/enrich/extractive.py`, add a constant near the other module constants (after `_MMR_THRESHOLD`):

```python
_TLDR_MAX = 3  # the TL;DR is always a mini 1-3 sentence lead, independent of source length
```

Replace `_select` (the whole function) with:

```python
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

    final = []
    for i, (rank, ws) in enumerate(zip(ranks, word_sets, strict=True)):
        lead_bonus = 0.15 * (1 - i / lead)
        overlap = len(ws & title_words) / (len(title_words) + 1)
        cue = 0.6 if any(c in sentences[i].lower() for c in _THESIS_CUES) else 0.0
        final.append(rank * (1 + lead_bonus + 0.3 * overlap + cue))

    n = len(sentences)
    n_kp = max(kp_min, min(kp_max, round(ratio * n)))
    n_tldr = min(_TLDR_MAX, n)
    target = n_tldr + n_kp
    order = sorted(range(n), key=lambda i: final[i], reverse=True)

    picked: list[int] = []
    for i in order:
        if len(picked) >= target:
            break
        if any(_similarity(word_sets[i], word_sets[p]) > _MMR_THRESHOLD for p in picked):
            continue
        picked.append(i)
    if not picked:
        picked = [order[0]]

    n_tldr = min(n_tldr, len(picked))
    tldr_idx = sorted(picked[:n_tldr])
    kp_idx = sorted(picked[n_tldr:])
    return [sentences[i] for i in tldr_idx], [sentences[i] for i in kp_idx]
```

Then update `ExtractiveSummarizer.summarize` signature + the `_select` call:

```python
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
```

- [ ] **Step 5: Update the ollama summarizer signature**

In `any2md/enrich/ollama.py`, change the `summarize` signature (it ignores the new args — its prompt already uses `ratio`):

```python
    def summarize(
        self, title: str, body: str, *, ratio: float = 0.2, kp_min: int = 3, kp_max: int = 20
    ) -> dict:
```

- [ ] **Step 6: Thread bounds through the enricher**

In `any2md/enrich/enricher.py`, update both functions:

```python
def enrich(
    doc: Document, summarizer: Summarizer | None, ratio: float = 0.2, kp_min: int = 3, kp_max: int = 20
) -> bool:
    if summarizer is None:
        return True
    try:
        data = summarizer.summarize(
            doc.title, doc.body_markdown, ratio=ratio, kp_min=kp_min, kp_max=kp_max
        )
        concepts = list(data.get("concepts") or [])
        doc.summary = inline_links(data.get("tldr") or "", concepts) or None
        doc.key_points = [inline_links(p, concepts) for p in (data.get("key_points") or [])]
        doc.tags = _normalize_tags(data.get("tags") or [])
        doc.wikilinks = concepts
        return True
    except Exception:
        return False


def enrich_with_fallback(
    doc: Document, provider: str, ratio: float = 0.2, kp_min: int = 3, kp_max: int = 20
) -> None:
    if not enrich(doc, get_summarizer(provider), ratio, kp_min, kp_max) and provider == "ollama":
        doc.warnings.append("ollama summarize failed — used extractive instead")
        enrich(doc, get_summarizer("extractive"), ratio, kp_min, kp_max)
```

- [ ] **Step 7: Pass per-level bounds from the pipeline**

In `any2md/pipeline.py`, change the import on line 7:

```python
from any2md.depth import bounds as depth_bounds
from any2md.depth import ratio as depth_ratio
```

Then change the enrich call (currently line 43-44):

```python
    if not is_raw(level):
        kp_min, kp_max = depth_bounds(level)
        enrich_with_fallback(doc, provider, depth_ratio(level), kp_min, kp_max)
```

- [ ] **Step 8: Run the new test + the full suite**

Run: `.venv/bin/pytest tests/test_extractive_quality.py -v && .venv/bin/pytest -q`
Expected: the new test PASSES; existing tests stay green (ratio-only callers use the wide 3-20 default band, so they still see depth differences).

- [ ] **Step 9: Commit**

```bash
git add any2md/enrich/ any2md/pipeline.py tests/test_extractive_quality.py
git commit -m "fix: depth clamp + fixed mini TL;DR (low<medium<high, capped); thread kp bounds"
```

---

## WS2 — Extractive quality (no leakage)

### Task 3: Strip HTML, bylines, emails, captions; de-glue; fix phrases + tags

**Files:**
- Modify: `any2md/enrich/extractive.py` (`_clean_prose`, `_key_phrases`, `_tags`, new regexes/helpers)
- Test: `tests/test_extractive_quality.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_extractive_quality.py`:

```python
def test_html_and_bylines_and_emails_do_not_leak():
    from any2md.enrich.extractive import ExtractiveSummarizer

    body = (
        '<a href="https://x.com"><img src="logo.png"></a> '
        "Focus on building applications, not infrastructure, with this framework. "
        "**nefele** I saw your demo at the conference and it looked great overall. "
        "AshishVaswani noam@google.com NikiParmar affiliations listed here. "
        "Figure 3 shows the attention heatmap across layers in detail. "
        "The framework provides automatic validation and serialization for requests."
    )
    out = ExtractiveSummarizer().summarize("Framework Overview", body, ratio=0.5, kp_min=3, kp_max=20)
    blob = out["tldr"] + " " + " ".join(out["key_points"]) + " " + " ".join(out["tags"])
    assert "<" not in blob and ">" not in blob          # no HTML tags/attributes
    assert "**" not in blob                              # no markdown bold bylines
    assert "nefele" not in blob                          # the byline word itself is gone
    assert "@google.com" not in blob and "noam" not in blob  # author/email block dropped
    assert "Figure 3" not in blob                        # figure caption dropped


def test_keyphrases_drop_camelcase_authors_and_do_not_merge_across_sentences():
    from any2md.enrich.extractive import _key_phrases

    prose = "We used Multi Head Attention. Generators are lazy. Iterables come first."
    phrases = _key_phrases(prose, "Title")
    assert "AshishVaswani" not in phrases
    assert all(" When" not in p and "Iterables Generators" not in p for p in phrases)


def test_deglue_splits_long_runon_tokens_only():
    from any2md.enrich.extractive import _deglue

    assert "BLEU" in _deglue("ourmodelachievesanewBLEUscoreofManyThings").replace(" ", " ")
    assert _deglue("GitHub") == "GitHub"  # short legit CamelCase untouched


def test_tags_drop_singletons_and_nonalpha():
    from any2md.enrich.extractive import _tags

    prose = "transformer transformer attention attention attention wmt2014 gpus."
    tags = _tags(prose, "Title", [])
    assert "attention" in tags
    assert "wmt2014" not in tags  # non-alpha dropped
```

- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/bin/pytest tests/test_extractive_quality.py -k "leak or camelcase or deglue or singletons" -v`
Expected: FAIL — HTML/byline leak through; `_deglue` does not exist.

- [ ] **Step 3: Add regexes + `_deglue`, harden `_clean_prose`**

In `any2md/enrich/extractive.py`, add near the other compiled patterns (after `_URL`):

```python
_HTML_TAG = re.compile(r"<[^>]+>")
_BOLD = re.compile(r"\*\*[^*]+\*\*")  # **author** bylines (HN/Reddit) and bold runs
_EMAIL = re.compile(r"\S+@\S+\.\S+")
_FIG_CAP = re.compile(r"^\s*(figure|fig\.|table)\s+\d+", re.I)


def _deglue(text: str) -> str:
    """Re-insert spaces inside abnormally long run-on tokens (markitdown drops them on some PDFs).
    Only tokens > 18 chars are touched, so legitimate words and short CamelCase stay intact."""

    def split(tok: str) -> str:
        if len(tok) <= 18:
            return tok
        tok = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", tok)
        tok = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", tok)
        tok = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", tok)
        return tok

    return " ".join(split(t) for t in text.split())
```

Then in `_clean_prose`, replace the final part of the loop body (the `kept.append(s)` and the lines just before the `for`-loop's `kept.append`) so the loop ends like this:

```python
        if _BOILERPLATE.search(s):
            continue
        if _FIG_CAP.match(s):  # "Figure 3 ...", "Table 2 ..." captions
            continue
        s = _BOLD.sub(" ", s)  # drop **author** bylines / bold runs
        s = _HTML_TAG.sub(" ", s)  # drop HTML tags + stray attribute fragments
        if _EMAIL.search(s):  # author / affiliation / contact lines
            continue
        s = s.strip()
        if not s:
            continue
        kept.append(s)
    text = _URL.sub(" ", " ".join(kept))
    text = _deglue(text)
    return re.sub(r"\s+", " ", text).strip()
```

- [ ] **Step 4: Harden `_key_phrases` (per-sentence; drop camelCase authors)**

In `any2md/enrich/extractive.py`, replace `_key_phrases` with:

```python
def _key_phrases(prose: str, title: str) -> list[str]:
    title_low = title.lower()
    mid_caps = {m.lower() for m in re.findall(r"[a-z0-9,]\s+([A-Z][a-zA-Z0-9]+)", prose)}

    cleaned: list[str] = []
    # Scan sentence-by-sentence so a phrase never merges across a sentence/heading boundary
    # (that produced junk like "Iterables When").
    for sentence in re.split(r"(?<=[.!?])\s+", prose):
        for phrase in re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b", sentence):
            words = phrase.split()
            while words and words[0].lower() in _STOPWORDS:
                words = words[1:]
            if not words:
                continue
            if any(re.search(r"[a-z][A-Z]", w) for w in words):  # camelCase author tokens
                continue
            candidate = " ".join(words)
            low = candidate.lower()
            if len(candidate) <= 2 or low in title_low or low in _STOPWORDS:
                continue
            if low in _COMMON_PROPER:
                continue
            if len(words) == 1 and words[0].lower() not in mid_caps:
                continue
            cleaned.append(candidate)
    counts = Counter(cleaned)
    ranked = sorted(counts, key=lambda p: (len(p.split()) > 1, counts[p]), reverse=True)
    return ranked[:_MAX_WIKILINKS]
```

- [ ] **Step 5: Denoise `_tags` (alpha-only, drop singletons)**

In `any2md/enrich/extractive.py`, in `_tags`, change the `freq` comprehension and the second loop:

```python
    freq = Counter(
        w
        for w in _content(prose)
        if w not in title_words and len(w) >= 4 and w not in _GENERIC and w.isalpha()
    )
```

and, in the loop that adds frequent words, stop at singletons:

```python
    for word, count in freq.most_common():  # then distinctive frequent words
        if len(chosen) >= _MAX_TAGS:
            break
        if count < 2:  # a word seen once is rarely a real topic tag
            break
        _add(word)
    return chosen[:_MAX_TAGS]
```

- [ ] **Step 6: Run the WS2 tests + full suite**

Run: `.venv/bin/pytest tests/test_extractive_quality.py -v && .venv/bin/pytest -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add any2md/enrich/extractive.py tests/test_extractive_quality.py
git commit -m "fix: strip HTML/bylines/emails/captions, de-glue run-ons, harden wikilinks+tags"
```

---

## WS3 — Handler robustness

### Task 4: GitHub follows redirects; pipeline skips on HTTP errors; docx covered

**Files:**
- Modify: `any2md/handlers/github.py:21,27,36`
- Modify: `any2md/pipeline.py` (extract try/except — extends the usability plan's block)
- Test: `tests/test_github.py`, `tests/test_pipeline.py`, `tests/test_files_handler.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_github.py`:

```python
def test_github_fetches_follow_redirects(monkeypatch):
    import any2md.handlers.github as gh

    seen = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {}

    def fake_get(url, **kwargs):
        seen[url] = kwargs
        return _Resp()

    monkeypatch.setattr(gh.httpx, "get", fake_get)
    gh._fetch_repo("octocat", "Hello-World")
    assert all(kw.get("follow_redirects") is True for kw in seen.values())
```

Add to `tests/test_pipeline.py`:

```python
def test_convert_skips_on_http_status_error(tmp_path, monkeypatch):
    import httpx

    from any2md import pipeline, registry

    class _Boom:
        def extract(self, target):
            req = httpx.Request("GET", "https://api.github.com/repos/x/y")
            raise httpx.HTTPStatusError("404", request=req, response=httpx.Response(404, request=req))

    monkeypatch.setattr(registry, "detect", lambda target: _Boom())
    events = []
    out = pipeline.convert("https://github.com/x/y", str(tmp_path), "none", on_event=events.append)
    assert out is None
    assert any(e.startswith("warn:skipped") for e in events)
```

Add to `tests/test_files_handler.py`:

```python
def test_files_handler_docx_maps_source_type(tmp_path, monkeypatch):
    doc_path = tmp_path / "report.docx"
    doc_path.write_bytes(b"PK\x03\x04")  # zip magic; convert is mocked
    h = FilesHandler()
    monkeypatch.setattr(
        h._md, "convert", lambda *a, **k: _FakeResult(title="Report", text="Quarterly update.")
    )
    doc = h.extract(str(doc_path))
    assert doc.source_type == "docx"
    assert "Quarterly" in doc.body_markdown
```

- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/bin/pytest tests/test_github.py::test_github_fetches_follow_redirects tests/test_pipeline.py::test_convert_skips_on_http_status_error -v`
Expected: FAIL — fetches lack `follow_redirects`; the pipeline lets the httpx error escape.

- [ ] **Step 3: Add `follow_redirects=True` in `github.py`**

In `any2md/handlers/github.py`, add `follow_redirects=True` to each of the three `httpx.get(...)` calls (`_fetch_repo`, `_fetch_readme`, `_fetch_languages`). Example for `_fetch_repo`:

```python
    resp = httpx.get(f"{_API_BASE}/repos/{owner}/{repo}", headers=_HEADERS, follow_redirects=True, timeout=15)
```

Apply the same `follow_redirects=True` argument to the `_fetch_readme` and `_fetch_languages` `httpx.get` calls.

- [ ] **Step 4: Extend the pipeline's extract guard**

In `any2md/pipeline.py`, add `import httpx` at the top (with the other imports), and extend the try/except around `handler.extract` (introduced in the usability plan) to also catch HTTP status errors:

```python
    try:
        doc = handler.extract(target)
    except SourceUnavailable as exc:
        emit("warn:skipped: " + str(exc))
        return None
    except httpx.HTTPStatusError as exc:
        emit(f"warn:skipped: source unavailable (HTTP {exc.response.status_code})")
        return None
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_github.py tests/test_pipeline.py tests/test_files_handler.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add any2md/handlers/github.py any2md/pipeline.py tests/test_github.py tests/test_pipeline.py tests/test_files_handler.py
git commit -m "fix: github follows redirects; pipeline skips cleanly on HTTP errors; cover docx"
```

---

## WS4 — Reddit / YouTube

### Task 5: Reddit old.reddit retry + clean skip

**Files:**
- Modify: `any2md/handlers/reddit.py` (add `_old_reddit`, rewrite `extract`)
- Test: `tests/test_reddit.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_reddit.py`:

```python
def test_old_reddit_swaps_host():
    from any2md.handlers.reddit import _old_reddit

    assert (
        _old_reddit("https://www.reddit.com/r/x/comments/abc/t/")
        == "https://old.reddit.com/r/x/comments/abc/t/"
    )


def test_total_block_raises_source_unavailable(monkeypatch):
    import httpx

    import any2md.handlers.reddit as rd
    from any2md.errors import SourceUnavailable

    def boom(url):
        req = httpx.Request("GET", url)
        raise httpx.HTTPStatusError("403", request=req, response=httpx.Response(403, request=req))

    monkeypatch.setattr(rd, "_fetch_json", boom)
    monkeypatch.setattr(rd, "_fetch_rss", boom)
    with pytest.raises(SourceUnavailable):
        rd.RedditHandler().extract("https://www.reddit.com/r/x/comments/abc/title/")
```

(Ensure `import pytest` is present at the top of `tests/test_reddit.py`.)

- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/bin/pytest tests/test_reddit.py::test_old_reddit_swaps_host tests/test_reddit.py::test_total_block_raises_source_unavailable -v`
Expected: FAIL — `_old_reddit` missing; total block currently raises raw `httpx.HTTPError`.

- [ ] **Step 3: Implement the retry + clean skip**

In `any2md/handlers/reddit.py`, add the import near the top:

```python
from any2md.errors import SourceUnavailable
```

Add the helper (near `_subreddit_from_url`):

```python
def _old_reddit(url: str) -> str:
    """Swap the host to old.reddit.com — its .json is blocked less aggressively."""
    return re.sub(r"https?://(www\.)?reddit\.com", "https://old.reddit.com", url)
```

Replace `RedditHandler.extract` with:

```python
    def extract(self, target: str) -> Document:
        try:
            return _extract_json(target, _fetch_json(target))
        except httpx.HTTPError:
            pass
        try:  # old.reddit.com is blocked less often than www
            return _extract_json(target, _fetch_json(_old_reddit(target)))
        except httpx.HTTPError:
            pass
        try:  # last resort: the keyless Atom feed (flat, no scores)
            return _extract_rss(target, _fetch_rss(target))
        except httpx.HTTPError as exc:
            raise SourceUnavailable(f"reddit blocked this request ({exc})") from exc
```

- [ ] **Step 4: Run the tests + the existing reddit suite**

Run: `.venv/bin/pytest tests/test_reddit.py -v`
Expected: PASS (new tests + existing ones; the existing `.json`→`.rss` fallback test still passes because the old.reddit attempt also raises under the same mock and falls through to `.rss`).

- [ ] **Step 5: Commit**

```bash
git add any2md/handlers/reddit.py tests/test_reddit.py
git commit -m "fix: reddit retries old.reddit then degrades to a clean skip (SourceUnavailable)"
```

### Task 6: YouTube JS-runtime detection + Docker deno

**Files:**
- Modify: `any2md/handlers/youtube.py` (add `js_runtime_available`, refine no-caption warning)
- Modify: `Dockerfile`
- Test: `tests/test_youtube.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_youtube.py`:

```python
def test_js_runtime_available_detects_deno(monkeypatch):
    from any2md.handlers import youtube

    monkeypatch.setattr(youtube.shutil, "which", lambda name: "/usr/bin/deno" if name == "deno" else None)
    assert youtube.js_runtime_available() is True

    monkeypatch.setattr(youtube.shutil, "which", lambda name: None)
    assert youtube.js_runtime_available() is False
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/pytest tests/test_youtube.py::test_js_runtime_available_detects_deno -v`
Expected: FAIL — `js_runtime_available` does not exist.

- [ ] **Step 3: Add the helper and refine the warning**

In `any2md/handlers/youtube.py`, add the helper (after `_get_captions`):

```python
def js_runtime_available() -> bool:
    """yt-dlp needs a JS runtime (deno/node) for reliable extraction on current YouTube."""
    return bool(shutil.which("deno") or shutil.which("node"))
```

Then replace the no-caption warning block in `extract` (currently lines 88-90):

```python
        warnings: list[str] = []
        if not captions:
            if not js_runtime_available():
                warnings.append(
                    "youtube extraction is degraded without a JS runtime — install deno"
                )
            elif shutil.which("ffmpeg") is None:
                warnings.append("no captions found; install ffmpeg for audio transcription")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_youtube.py -v`
Expected: PASS

- [ ] **Step 5: Install deno in the Docker image**

Open `Dockerfile`. After the existing system-dependency install layer (the `apt-get install ... ffmpeg ... tesseract-ocr` line), add a deno install layer:

```dockerfile
# yt-dlp's default JS runtime (reliable YouTube extraction). DENO_INSTALL pins the location.
ENV DENO_INSTALL=/usr/local
RUN curl -fsSL https://deno.land/install.sh | sh
```

If the base image lacks `curl`, add `curl` to the `apt-get install` list on the preceding line.

- [ ] **Step 6: Commit**

```bash
git add any2md/handlers/youtube.py Dockerfile tests/test_youtube.py
git commit -m "fix: detect JS runtime for youtube; install deno in Docker; clearer no-caption hint"
```

---

## WS5 — Verification + release prep

### Task 7: Full verification and version bump

- [ ] **Step 1: Run the entire suite + lint**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`
Expected: all pass, zero lint errors.

- [ ] **Step 2: Live re-test scorecard (real network)**

Run the harness on the same sources as the spec's baseline and eyeball the summaries:
```bash
.venv/bin/python /tmp/a2m_harness.py \
  "ARXIV=https://arxiv.org/abs/1706.03762" \
  "GITHUB=https://github.com/tiangolo/fastapi" \
  "WEB=https://karpathy.github.io/2015/05/21/rnn-effectiveness/" \
  "PDF=/tmp/attention.pdf"
```
Expected: GitHub (renamed repo) converts via redirect; web TL;DR is <= 3 sentences with <= 20 key points; no `<`/`**`/email leakage anywhere. Confirm every testable format reads >= 78/100.

- [ ] **Step 3: Update `.claude/rules/output-format.md` depth line**

In `.claude/rules/output-format.md`, the depth line says "low 10% · medium 20% · high 35%". This now matches `depth.py` — confirm it reads correctly; fix the percentages if they drifted.

- [ ] **Step 4: Bump the version (so it isn't a hollow 0.1.1)**

In `any2md/__init__.py`, set:

```python
__version__ = "0.1.2"
```

- [ ] **Step 5: Commit**

```bash
git add any2md/__init__.py .claude/rules/output-format.md
git commit -m "chore: bump version to 0.1.2 for quality + robustness release"
```

---

## Self-Review (completed)

- **Spec coverage:** WS1 depth floor + unbounded TL;DR + ratio mismatch → Tasks 1-2. WS2 HTML/boilerplate/byline/glue/wikilink/tag → Task 3. WS3 GitHub redirects + graceful 4xx + docx → Task 4. WS4 Reddit + YouTube → Tasks 5-6. Verification + version → Task 7. All spec items mapped.
- **Placeholders:** none — every code step shows full code; the only file-dependent step (Dockerfile) includes the snippet and exact placement.
- **Type consistency:** `summarize(..., ratio, kp_min, kp_max)` identical across `base.py`, `extractive.py`, `ollama.py`; `enrich`/`enrich_with_fallback` pass the same names; `depth.bounds()` returns `(int, int)` consumed as `kp_min, kp_max`; `_deglue`, `js_runtime_available`, `_old_reddit` signatures match their tests.
- **Dependency note:** WS3/WS4 reuse `any2md/errors.py:SourceUnavailable` and the pipeline `try/except` from the usability plan (Task 2 there). Build the usability plan first, or create `errors.py` + the try/except before WS3.
```
