# Any2MD — Quality + Robustness Overhaul

Date: 2026-05-30
Author: Altrin Titus (design w/ Claude)
Status: Approved — ready for implementation plan

---

## Context

A full live-conversion review of the shipped CLI (v0.1.0) surfaced one user-reported bug
(`/depth` does nothing) plus a cluster of summary-quality and handler-robustness defects.
Every format was converted with the `extractive` provider against real sources and rated.

### Evidence — live test scorecard (extractive, medium depth)

| Format | Status | Accuracy | Main problem |
|---|---|---:|---|
| CSV | ok | 90 | Correct passthrough of table — no false distill |
| arXiv | ok | 88 | Clean thesis-led TL;DR; weak tags (`wmt`, `gpus`) |
| Twitter | ok | 80 | Live tweet fine (passthrough); hard-errors on dead tweet |
| YouTube | ok | 72 | Works + transcript; weak tags on speech; JS-runtime deprecation looms |
| Wikipedia | ok | 70 | Accurate but trivial — distills an already 1–2 sentence source |
| Stack Overflow | ok | 68 | Broken wikilinks (`Iterables When`); fragment key-points |
| Web article | ok | 62 | 20-sentence TL;DR + 59 key points — not "distilled" |
| Hacker News | ok | 60 | ~15s slow; commenter usernames (`**nefele**`) leak into TL;DR |
| PDF | ok | 38 | markitdown glues words; author/email block as KP1; garbage tags |
| GitHub | FAIL | 30 | Crashes on renamed repos (no `follow_redirects`); HTML READMEs → tag-soup |
| Reddit | FAIL | 25 | 403 from server networks on **both** `.json` and `.rss`; hard crash |
| DOCX | — | n/a | Untested — no sample locally |

Testable average ≈ 60/100.

### Root causes

1. **Depth floor** — `extractive._select` uses `max_picks = max(8, min(n, round(ratio*n)))`.
   The `max(8, …)` floor swamps the ratio: proven that `low` and `medium` produce
   **byte-identical** output for any source under ~28 clean sentences (~600+ words), which is
   most inputs. Only `high` ever diverges. This is the user-reported "`/depth` does nothing."
2. **Unbounded output** — `n_tldr = ceil(picks*0.25)` and `picks` scale with document length,
   so a long article yields a 20-sentence "TL;DR" and 59 key points (spec calls for a *mini*
   TL;DR + distilled key points).
3. **Ratio mismatch** — `depth.py` defines medium=0.30 / high=0.50, but
   `.claude/rules/output-format.md` documents medium 20% / high 35%.
4. **No HTML stripping** — `_clean_prose` strips markdown structure but not raw HTML, so
   README/web HTML (`<img src=`, `<a href=`, `<div>`) leaks into the summary.
5. **No PDF de-glue / boilerplate filter** — markitdown loses inter-word spaces on some PDFs
   (`ourmodelestablishes…`), and author/affiliation/email blocks are treated as prose
   (KP1 = the author byline).
6. **Broken wikilink extraction** — `_key_phrases` merges heading-adjacent capitalized words
   (`Iterables When`, `Generators Generators`) and captures ALL-CAPS author names
   (`AshishVaswani`).
7. **Weak tags** — generic/noise tokens survive (`creating`, `formatted`, `href`, `something`,
   `wmt`, `gpus`).
8. **GitHub no `follow_redirects`** — `_fetch_repo/_fetch_readme/_fetch_languages` call
   `httpx.get(...)` without `follow_redirects=True`; a renamed repo (301) crashes the convert.
9. **Handlers raise raw `HTTPStatusError`** on 4xx instead of degrading to a clean skip — the
   handler contract says catch `httpx.HTTPError` and fall back / degrade gracefully.
10. **Reddit effectively dead from server IPs** — both `.json` and `.rss` return 403.
11. **HN usernames leak** — comment author bylines (`**nefele**`) survive into the summary.
12. **yt-dlp JS-runtime deprecation** — yt-dlp warns that extraction without a JS runtime
    (deno/node) is deprecated; future YouTube breakage.

---

## Goals & success criteria (measurable)

- **Depth is monotonic & visible:** for every source, `key_points(low) < key_points(medium) <
  key_points(high)`; TL;DR is always 2–3 sentences regardless of depth or source length.
- **No leakage:** rendered summaries contain no HTML tags, no email/author-affiliation blocks,
  no `**username**` bylines, no glued-word runs above a small threshold.
- **No hard crashes:** dead / blocked / renamed sources produce a clean
  `skipped: <reason>` (no `HTTPStatusError` traceback reaches the user).
- **Accuracy bar:** every testable format scores **≥ 78/100** on the post-fix live re-test;
  externally-blocked Reddit is allowed to remain honest best-effort (documented, not crashing).
- **No regressions:** existing `pytest` suite stays green; `render()` golden tests still pass.

## Hard constraints (unchanged, must hold)

- 100% free / open-source. **No external APIs, no API keys, ever** (rules out Reddit OAuth).
- Summarization is best-effort: any summarizer/Ollama error still yields extraction-only output.
- Output frontmatter always includes `source_url`, `source_type`, `extraction_date`.
- No live network in tests — mock `_fetch_*`, use fixtures under `tests/fixtures/`.
- Handlers do extraction only — no summarizing, no file writing.

---

## Approach

One spec, **four sequenced workstreams**, re-measuring the /100 scorecard after each phase.
WS1 and WS2 both edit `extractive.py` and land together; WS3 and WS4 are independent follow-ons.

### WS1 — Depth distillation `(any2md/depth.py, any2md/enrich/extractive.py)`

Replace the floor with a per-level clamp and decouple the TL;DR length.

`depth.py` — new level table (also resolves the ratio mismatch; update
`.claude/rules/output-format.md` to match):

| level | ratio | min KP | max KP |
|---|---:|---:|---:|
| low | 0.10 | 3 | 6 |
| medium | 0.20 | 6 | 12 |
| high | 0.35 | 10 | 20 |

`_select` algorithm change:
- `n_kp = clamp(round(ratio * n), kp_min, kp_max)` — key-point budget, never collapses across
  levels, never explodes on long sources.
- TL;DR = the top **2–3** ranked sentences (a fixed small count, independent of `n_kp`), chosen
  before key-points and excluded from them.
- Key-points = the next `n_kp` ranked non-redundant sentences (existing MMR dedup retained).
- Carry the per-level `(ratio, min, max)` from `depth.py` into the summarizer (extend
  `Summarizer.summarize` to accept the budget, or pass a resolved `(n_min, n_max)` alongside
  `ratio`). Keep `ratio` default so direct callers/tests still work.

Thread depth explicitly end-to-end:
- `JobQueue.submit(target, output_dir, provider, depth=None)` and `Job.depth`; `_default_convert`
  forwards `depth` to `pipeline.convert`. (Today depth only reaches the pipeline via `config`;
  it works but is implicit. Make it explicit so REPL/serve/CLI all behave identically.)
- `Repl.handle` / `_convert_with_progress` pass `self.depth`.

Acceptance: monotonic counts on a short (≈25-sentence) and a long (≈200-sentence) fixture;
TL;DR ≤ 3 sentences in all cases.

### WS2 — Extractive quality `(any2md/enrich/extractive.py)`

- **HTML strip in `_clean_prose`:** remove HTML comments, tags, and stray attribute fragments
  (`<...>`, `href="..."`, `src="..."`) before sentence splitting. Fixes GitHub/web tag-soup.
- **Boilerplate filter:** drop lines that are emails, author/affiliation runs (≥3 capitalized
  tokens with no verb / containing `@`), and `Figure N` / `Table N` captions.
- **Glued-text guard:** if a line's space ratio is abnormally low, insert spaces at
  `lower→Upper` and `letter↔digit` boundaries (light touch). Explicitly **no** dictionary
  word-segmentation — see Limits.
- **`_key_phrases` fix:** require a genuine mid-sentence capital (already partly done), reject
  ALL-CAPS / camelCase author-style tokens (`AshishVaswani`), and never span a line/heading
  boundary when forming a phrase (kills `Iterables When`).
- **Tag denoise:** extend `_GENERIC`, drop tokens derived from URLs/HTML, require a minimum
  document frequency, and prefer the cleaned concept phrases.

Acceptance: GitHub (HTML README), PDF (arXiv), Web, SO fixtures produce summaries with zero
HTML/email/byline leakage and sensible tags.

### WS3 — Handler robustness

- **GitHub:** add `follow_redirects=True` to all three `_fetch_*` calls. Fixes renamed-repo
  301 crash (e.g. `tiangolo/fastapi` → `fastapi/fastapi`).
- **Graceful degradation:** introduce a typed `SourceUnavailable(reason)` (in
  `handlers/base.py` or `errors.py`). Handlers catch `httpx.HTTPStatusError` for 403/404/410
  and raise `SourceUnavailable`; `pipeline.convert` catches it and emits
  `warn:skipped: <reason>` + returns `None` (clean skip, no traceback). CLI/REPL already render
  warnings.
- **HN:** strip `**username**` author bylines from `body_markdown` before enrichment.
- **DOCX:** add a generated `.docx` fixture (build it in a test helper) and an e2e test so the
  files-handler docx path is actually covered.

Acceptance: renamed GitHub repo converts; a 404 source yields a clean skip line; HN summary
has no bylines; docx e2e passes.

### WS4 — Reddit / YouTube (best-effort, no keys)

- **Reddit:** send a browser-like `User-Agent`; try `old.reddit.com/<permalink>.json` before
  the `.rss` fallback; if all return 403/404, raise `SourceUnavailable` (clean skip via WS3).
  Honest note: some networks hard-block Reddit with no keyless workaround.
- **YouTube:** detect `deno` or `node` on `PATH`; when present, pass it to yt-dlp as the JS
  runtime to silence the deprecation and future-proof extraction. Add `deno` to the Dockerfile.
  Keep best-effort; geo/age-gated videos still fail per-video.

Acceptance: Reddit either extracts (when reachable) or skips cleanly; YouTube runs without the
JS-runtime warning when a runtime is installed.

---

## Verification

- **Fixture quality harness** (`tests/test_summary_quality.py`, no live network): saved real
  bodies per format → assert depth monotonicity, TL;DR ≤ 3, key-points within per-level caps,
  and zero HTML/email/byline leakage (regex tripwires). This is the permanent guard.
- **One-time live re-test:** re-run today's live conversions after each phase and report the new
  /100 scorecard (target: every testable format ≥ 78).
- **No regressions:** `pytest -q` and `ruff check .` green; `render()` golden tests unchanged.

## Out of scope / honest limits

- Arbitrary PDF word de-gluing (a pdfminer/markitdown artifact; true fix needs a segmentation
  model). We filter boilerplate + apply light boundary spacing only.
- Networks that hard-block Reddit at the IP level — no keyless fix exists.
- Per-video YouTube failures (geo/age/bot gates) — out of our control.
- No new summarizer providers, no API keys, no paid services.

## Testing strategy (TDD per workstream)

- WS1: unit tests on `depth.ratio`/clamp + `_select` monotonicity on short/long fixtures.
- WS2: `_clean_prose` / `_key_phrases` / `_tags` unit tests on HTML, PDF-glue, author-block,
  heading-boundary fixtures.
- WS3: GitHub redirect test (mock 301 → 200); `SourceUnavailable` → clean skip e2e; HN byline
  strip; docx e2e.
- WS4: Reddit UA/old.reddit path with mocked `_fetch_*` (403 → skip); YouTube runtime-detection
  unit test (mock `shutil.which`).
- Each phase ends only when its tests + the full suite are green.

## Phasing (suggested)

1. WS1 (depth) — smallest, fixes the reported bug; re-measure.
2. WS2 (extractive quality) — biggest quality lift; re-measure.
3. WS3 (handler robustness) — re-measure.
4. WS4 (Reddit/YouTube) — best-effort; re-measure.
