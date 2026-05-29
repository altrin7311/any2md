# Design — Any2MD launch polish (9 workstreams)

> Make Any2MD launch-ready for GitHub. Foundation is solid (212 tests green, polished REPL,
> both 2026-05-29 designs implemented). This closes the gap between "works great sometimes"
> and "works great consistently." **Quality bar = the extractive summarizer** (most users
> won't run Ollama). Hard constraints unchanged: 100% free/OSS, no external APIs/keys,
> summarization best-effort (never hard-fail), TDD with no live network in tests, suite stays
> green. **Implementer does NOT commit — the user does.**

## Decisions (locked with user)

- Scope: all of A (quality) + B (robustness) + C (UX) + D (launch) + any further improvements found.
- **Extractive is the quality bar** — tune it to be genuinely good; ollama is a bonus tier.
- **Empty extraction → skip writing** + clear terminal warning (don't pollute the vault).
- **Canonicalize URLs** — strip tracking params (utm_/gclid/gad_/fbclid/gbraid/...), keep
  functional params (youtube `?v=`, SO `?answertab=`); dedup on the canonical URL.
- Tags normalized to valid Obsidian form (hyphenated lowercase).
- `/open` uses `open` (darwin) / `xdg-open` (linux) / `start` (windows).

## Evidence (from the user's own 4 sample outputs + offline repro)

- `the-ceos-guide-to-physical-ai.md` — target quality (TL;DR + Key Points + inlined links + tags).
- `attention-is-all-you-need.md` — raw `## Abstract` passthrough, `tags: []`. **Repro: extractive
  distills this abstract fine** → that file was a `provider=none`/`raw` artifact, not a pipeline
  bug. But the repro exposed the real extractive weaknesses below.
- Offline extractive on the attention abstract returned: tags `[models, based, best, translation,
  bleu, dominant]` (junk words), TL;DR = first two throat-clearing sentences, concepts `[BLEU,
  Transformer, WMT, English]` (noisy).
- `random-article-longform.md` — nav teaser, `tags: []`. `www-lifescience-net.md` — empty body,
  bare-domain title. The BCG tags `[Artificial Intelligence, Robotics, ...]` contain spaces →
  **invalid Obsidian tags** (silent bug).

---

## WS1 — Extractive quality (`any2md/enrich/extractive.py`)

The default summarizer must produce notes a stranger trusts.

- **Tags (`_tags`)**: pure frequency surfaces generic words (`based`, `best`, `dominant`).
  Replace with: blend the capitalized concept phrases (`_key_phrases`) + distinctive content
  words, drop a generic-adjective/common-word stoplist, allow multiword topics. Slugify at the
  end (see WS2). Target: attention abstract → `transformer`, `attention`, `machine-translation`.
- **TL;DR (`_select`)**: lead bias (`0.25 * (1 - i/lead)`) dominates on short docs, so the TL;DR
  leads with sentence 0 (throat-clearing) instead of the contribution. Reduce lead weight and/or
  pick the TL;DR by centrality (TextRank) rather than the blended lead-heavy score, so the
  contribution sentence ("we propose the Transformer…") leads.
- **Concepts (`_key_phrases`)**: filter noise — language names, bare single-word acronyms unless
  repeated; prefer repeated + multiword.
- **`max_picks` floor (`max(8, ...)`)**: makes low/medium identical on short docs. Lower the
  floor (e.g. `max(3, round(ratio*n))`, still ≥1) so depth levels visibly differ.

**Tests (`tests/test_extractive_quality.py`)**: a generic-word stoplist (`based/best/dominant/...`)
must not appear in tags; the contribution sentence appears in the TL;DR for the attention abstract;
concepts exclude `English`/`WMT`-style noise; low vs high ratio yield different sizes on a long doc.

## WS2 — Valid Obsidian tags (`any2md/enrich/enricher.py`)

Obsidian tags cannot contain spaces. Multiword tags (esp. from ollama) are silently broken.

- Add `normalize_tag(tag) -> str`: lowercase, spaces/underscores→hyphen, strip non `[a-z0-9-]`,
  collapse repeats, trim. Apply to every tag in `enrich()` (covers extractive AND ollama). Drop
  empties + dedupe preserving order.
- **Tests (`tests/test_enricher.py`)**: `Artificial Intelligence` → `artificial-intelligence`;
  enrich with a fake summarizer returning spaced tags → `doc.tags` all valid + deduped.

## WS3 — URL canonicalization + dedup (`any2md/url.py` new · `any2md/writer.py`)

- New `any2md/url.py` `canonical_url(url) -> str`: drop tracking query params
  (prefix `utm_`, plus `gclid`, `gclsrc`, `fbclid`, `gad_source`, `gad_campaignid`, `gbraid`,
  `wbraid`, `mc_eid`, `mc_cid`, `igshid`, `si`, `ref`, `ref_src`), drop the URL fragment, keep all
  other (functional) params and their order. Normalize scheme/host lowercase. Leave non-http
  untouched.
- Handlers store `canonical_url(target)` in `source_url` — done once in `pipeline.convert` after
  extract (set `doc.source_url = canonical_url(doc.source_url)` when it's an http(s) URL), so every
  handler benefits without touching each.
- `writer._find_by_source_url` already matches on the stored string → dedup now works across
  tracking variants.
- **Tests (`tests/test_url.py` new)**: utm_/gclid/fbclid/gbraid stripped; youtube `?v=` and SO
  `?answertab=votes` kept; fragment dropped; non-http unchanged. **`tests/test_writer.py`**: two
  URLs differing only by tracking params → ONE note (dedup), via the pipeline-canonicalized url.

## WS4 — Skip empty extractions (`any2md/pipeline.py`)

- `pipeline.convert`: if `is_low_content(doc.body_markdown)` AND, after enrich, nothing distilled
  (`not doc.summary and not doc.key_points and not doc.body_markdown.strip()` → truly empty),
  do NOT write. Emit `warn:extraction failed — source may be paywalled or JS-only; nothing written`
  and return `None`. (Low-content but non-empty, e.g. a short tweet, still writes — only the
  genuinely empty case is skipped.)
- Signature: `convert(...) -> Path | None`. Update callers:
  - `cli.convert`: `None` path → print the warning, don't print `✓ wrote`; count as a soft skip
    (not a failure exit).
  - `queue._run`: `result=None` with warnings present → job status `skipped` (new), surfaced by
    `/jobs` and `_convert_with_progress` (print warnings, no `✓` line).
- **Tests (`tests/test_pipeline.py`)**: mock a handler returning empty body → `convert` returns
  `None`, warning emitted, no file in the out dir. Non-empty short body → still writes.
  **`tests/test_queue.py`**: empty-result job → status `skipped`, warnings populated.

## WS5 — Better web titles (`any2md/handlers/web.py`)

- When trafilatura's title is missing/empty, fall back to the raw HTML `<title>` then first `<h1>`
  (parse from the already-downloaded HTML — no extra fetch). Strip trailing site suffixes
  (` | SiteName`, ` - SiteName`, ` — SiteName`) using the sitename when known. Bare domain only as
  the final fallback. Helper `_clean_title(raw, sitename) -> str` is pure + unit-tested;
  `_fetch_and_extract` returns the raw html so the handler can parse `<title>`/`<h1>`.
- **Tests (`tests/test_web_handler.py` or existing web test)**: `Foo | LifeScience` + sitename
  `LifeScience` → `Foo`; missing trafilatura title → `<title>`/`<h1>` used; only-domain when
  nothing else. Mock `_fetch_and_extract` (no network).

## WS6 — `/provider` validation + picker (`any2md/repl.py` · `any2md/cli.py`)

- `Repl._command` `/provider`: validate arg ∈ `{extractive, ollama, none}`; bad arg → usage
  string, provider unchanged; persist with `config.set_value("provider", arg)` so it sticks.
  No-arg on a TTY → a live picker (reuse the `/depth` prompt_toolkit pattern; `pragma: no cover`).
- `cli.convert`: add `--provider` option (overrides config for that run).
- **Tests (`tests/test_repl.py`)**: `/provider bogus` → usage, provider unchanged; `/provider none`
  → set + persisted (tmp `ANY2MD_CONFIG`). **`tests/test_cli.py`**: `--provider none` honored.

## WS7 — REPL UX (`any2md/repl.py` · `any2md/theme.py`)

- **TL;DR peek**: after a successful convert, print the first ~2 lines of the note's TL;DR (read
  from `job.result`, parse the `> [!summary]` block) dim, so the user sees the gist. Pure helper
  `tldr_peek(markdown) -> str` unit-tested.
- **`/open`**: open the output folder (no arg) or the last note (`/open last`) via the per-OS
  opener. Helper `_opener_cmd(platform) -> str` unit-tested; the subprocess call is `no cover`.
  Add `/open` to `_COMMANDS` + the `/help` palette (`theme.COMMANDS`).
- **Create-vs-update**: `writer.write` returns `(path, created: bool)` (or a small result); REPL
  prints `updated existing note` vs the normal `✓` when dedup overwrote. Keep `write`'s return
  back-compatible for other callers (return path; add `write_result` or a tuple — pick the
  least-disruptive; update all call sites + tests).
- **Graceful Ctrl-C during convert**: catch `KeyboardInterrupt` around `_convert_with_progress`
  so it cancels the in-flight job/spinner and returns to the prompt instead of killing the REPL.
- **Tests**: `tldr_peek` + `_opener_cmd` pure unit tests; writer create/update flag in
  `tests/test_writer.py`. Interactive bits `pragma: no cover`.

## WS8 — Robustness (handlers)

- Audit every `_fetch_*` for an httpx `timeout=` (arxiv has 15). Add a sane timeout (10–15s) +
  `follow_redirects=True` where missing across reddit/github/hackernews/wikipedia/stackoverflow/
  twitter. Best-effort already wraps failures; this stops indefinite hangs behind the spinner.
- Confirm the tesseract/ffmpeg missing-binary warnings (files.py/youtube.py) actually fire — add a
  test if not already covered.
- **Tests**: per-handler timeout is a code-review/grep check (no network); add a files.py
  tesseract-missing test if absent.

## WS9 — Launch readiness (`README.md` · `.github/` · `pyproject.toml`)

- **README**: rewrite as the storefront — one-line pitch, "no keys, ever" promise, animated demo
  placeholder (asciinema/GIF instructions), install (`pipx install any2md`), REPL + one-shot
  examples, the supported-sources table, summarizer tiers, `/depth`, config/env, serve/Docker note,
  contributing pointer, license.
- **CI**: `.github/workflows/ci.yml` — on push/PR, set up Python 3.11/3.12, install, run
  `pytest -q` + `ruff check .`.
- **Light governance**: `CONTRIBUTING.md` (dev setup, TDD rule, `/checks`), a bug-report issue
  template. README test/lint badges.
- **Packaging sanity**: verify `pyproject` entry point (`any2md = any2md.cli:main`), extras
  (`[serve]`), classifiers; smoke `python -c "import any2md.cli"` from the venv.

## Out of scope (deferred)

Clipboard convert · new sources · vault index/MOC note · frontmatter templating · batch live table.

## Execution order

WS3 → WS4 → WS2 → WS1 → WS5 → WS6 → WS7 → WS8 → WS9. (Backend/isolated first; quality next;
UX/launch last.) `pytest -q && ruff check .` green after every workstream.

## Notes for the implementer

- User commits/pushes themselves — **do not commit**.
- Run via the project venv: `.venv/bin/python -m pytest -q` and `.venv/bin/python -m ruff check .`.
- `.claude/hooks/ruff.sh` strips unused imports on edited `.py` — add an import in the same edit
  that uses it.
- Isolate global state in tests with `ANY2MD_CONFIG` / `ANY2MD_STATS` → tmp paths.
- Keep golden render tests byte-exact; warnings never render into the `.md`.
