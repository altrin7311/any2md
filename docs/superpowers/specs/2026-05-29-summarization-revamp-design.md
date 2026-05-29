# Design — Summarization revamp + `/depth`

> Turns Any2MD from "extract everything + a summary line" into "distill to a knowledge note."
> Hard constraints unchanged: 100% free/OSS, no external APIs/keys, summarization best-effort
> (never hard-fail), TDD, no live network in tests.

## Goal

Stop dumping the full source into the `.md`. Instead the note IS the distilled signal — the
important ~20% that carries ~80% of the meaning — laid out as an Obsidian second-brain note.
A new `/depth` command (low/medium/high, live `/effort`-style arrow picker) tunes how much is kept.

## Decisions (locked with user)

- **Output = distilled note only.** Raw full body dropped (lives at `source_url`).
- **Levels = pure % of source, no cap:** low **10%** · medium **20%** · high **35%**.
- **Structure:** `> [!summary] TL;DR` (mini multi-line summary) + `## Key Points` (bullets). **No
  separate Concepts section.** `[[wikilinks]]` are **inlined** into the TL;DR and bullets.
- **Tags** stay in frontmatter.
- **Command `/depth`:** persistent session/config setting; live arrow picker (scroll-bar like
  Claude `/effort`) with a greyed `~X% · ~N lines` hint; also `/depth <level>` arg form.
- **Key input:** stdlib `termios` raw reader — **no new dependency** (matches the stdlib-only
  stack). Live picker on a Unix TTY; non-TTY/scriptable falls back to the arg/flag/env forms.
- **`provider=none`** stays an escape hatch → raw extraction passthrough, depth ignored.

---

## 1. Output format

`.claude/rules/output-format.md` is **reversed**: summary REPLACES the body (no longer augments).
One unified layout for every source (no per-source section headings any more):

```markdown
---
title: "Attention Is All You Need"
source_url: "https://arxiv.org/abs/1706.03762"
source_type: arxiv
upload_date: 2017-06-12
extraction_date: 2026-05-29
tags: [transformers, attention, nlp]
---
# Attention Is All You Need

> [!summary] TL;DR
> The [[Transformer]] drops recurrence entirely, relying on [[Self-Attention]]
> to relate tokens. It trains far faster and tops translation benchmarks.

## Key Points
- [[Self-Attention]] weighs all tokens in parallel
- No RNN/CNN → better long-range dependencies
- New SOTA on WMT14 [[Machine Translation]]
```

- Frontmatter keys unchanged except the body. Type-specific metadata lift (channel/stars/…) stays.
- **Tabular / structured / tiny sources** (csv, xlsx, json, xml, or anything with too little
  distillable prose) have nothing to summarize → the original body **passes through unchanged**
  (same as `provider=none` for that doc). Prevents empty notes for spreadsheets. The existing
  `extracted almost no content` warning (#6) still fires when truly empty.

## 2. Summarizer contract

`enrich/base.py`:
```python
def summarize(self, title: str, body: str, *, ratio: float = 0.2) -> dict:
    """Return {"tldr": str, "key_points": list[str], "tags": list[str], "concepts": list[str]}."""
```
- `tldr` — the mini summary (top sentences, prose).
- `key_points` — the remaining distilled sentences, one per bullet.
- `concepts` — phrases to inline as `[[links]]` (not rendered as a list).
- `tags` — frontmatter tags.

`Document` (models.py) changes:
- `summary: str | None` → now holds the **TL;DR** (with links inlined).
- **new** `key_points: list[str]` (with links inlined).
- `tags: list[str]` — unchanged.
- `wikilinks: list[str]` — now holds the raw `concepts` (kept for reference/inlining source; **not
  rendered as a section**).

## 3. Selection mechanics (extractive, keyless)

In `enrich/extractive.py`:
1. `_clean_prose` + `_split_sentences` as today.
2. Rank sentences (existing TextRank + lead + title blend).
3. **Budget = ratio × (total prose word count).** Greedily MMR-select sentences in score order
   until cumulative words ≥ budget → set `S`.
4. **TL;DR** = top `max(1, ceil(len(S) * 0.25))` sentences of `S` by score, in reading order,
   joined as prose.
5. **Key Points** = the remaining `S` sentences, reading order, one per bullet.
6. `concepts` = existing `_key_phrases`.
7. If prose is empty/structured → return empty tldr/key_points (triggers §1 passthrough).

**Ollama** (`enrich/ollama.py`): pass the ratio into the prompt ("keep ≈X% / ~N words; return JSON
with `tldr`, `key_points` (list), `concepts` (list), `tags` (list)"). True paraphrase tier.

## 4. Inlining `[[wikilinks]]`

New pure helper (in `enrich/enricher.py` or a small util), unit-tested:
```python
def inline_links(text: str, phrases: list[str]) -> str
```
- Wrap the **first whole-word, case-insensitive** occurrence of each phrase with `[[ ]]`,
  preserving the original casing inside the brackets.
- Skip a phrase already inside a `[[ ]]`; never double-wrap; never wrap inside another match.
- `enricher.enrich` runs `summarize`, inlines `concepts` into `tldr` + each `key_point`, then sets
  `doc.summary` (tldr), `doc.key_points`, `doc.tags`, `doc.wikilinks` (raw concepts).
- `enrich_with_fallback` (#2 work) is preserved: ollama down → extractive + warning.

## 5. Render (`render.py`)

- Frontmatter as today (tags line kept; no Concepts).
- Body: `# title`, then the `> [!summary] TL;DR` callout (each TL;DR line prefixed `> `), then
  `## Key Points` with `- ` bullets. Omit a section if empty.
- Passthrough docs (§1) render the raw `body_markdown` under `## Content` as before.
- `provider=none`: unchanged raw passthrough.

## 6. `/depth` command + live picker

- **State:** `depth` ∈ {low, medium, high}; ratios {0.10, 0.20, 0.35}. Default `medium`.
- **Precedence:** CLI `--depth` > env `ANY2MD_DEPTH` > `config.toml` `depth` > `medium`.
- **REPL `/depth`** (no arg, Unix TTY): live picker via `termios`/`tty` raw mode —
  ```
    summary depth

    low ────────●──────── high          ◀ ▶ change · enter confirm
                medium · ~20% of source · ~15 lines
  ```
  ◀ ▶ move the knob; greyed hint updates live. Enter commits to config; Esc/q cancels.
- **`~N lines`** = learned running average per level stored in `stats.json` (same file/mechanism
  `eta.py` uses); static fallback (low 6 / med 15 / high 30) until enough samples.
- **`/depth <level>`** (arg) sets directly — non-TTY safe, scriptable, the **unit-tested** path.
- **One-shot:** `any2md convert … --depth high`.
- Pipeline/queue pass the resolved ratio into `enrich` → `summarize`.

## 7. Files touched

`enrich/base.py` · `enrich/extractive.py` · `enrich/ollama.py` · `enrich/enricher.py` ·
`models.py` (`key_points`) · `render.py` · `repl.py` (`/depth` + picker) · `theme.py` (picker
render helper) · `config.py` (`depth` key) · `cli.py` (`--depth`) · `pipeline.py`/`queue.py`
(thread ratio through) · `.claude/rules/output-format.md` (reverse augment rule, document `/depth`).

## 8. Testing (TDD — no network)

| Area | Test |
|---|---|
| ratio→words | budget math: ratio × word count → expected sentence set size |
| TL;DR / Key Points split | top-quartile → tldr, rest → bullets; no overlap |
| inline_links | first-occurrence wrap, case-preserved, no double-wrap, phrase-not-found no-op |
| depth state | low↔medium↔high cycling; ratio lookup; precedence (flag>env>config>default) |
| hint text | `~X% · ~N lines` string; learned-avg fallback to static |
| render golden | new `> [!summary]` + `## Key Points` golden `.md` (update `test_render`) |
| structured passthrough | csv/xlsx body passes through unchanged (update `test_e2e_files`) |
| extractive output shape | `summarize` returns tldr/key_points/concepts/tags (update `test_extractive_quality`) |
| `/depth` arg | `handle("/depth high")` sets level (interactive raw loop = `pragma: no cover`) |

Run: `pytest -q && ruff check .`

## Out of scope

- Cross-platform (Windows) raw-key input — arg/flag fallback covers it.
- Re-summarizing an existing note in place without re-fetching (re-convert handles it via #3 dedup).
- Abstractive quality beyond what ollama gives.

## Notes for the implementer

- User commits/pushes themselves — **do not commit**. Show run commands as `||command||`.
- `.claude/hooks/ruff.sh` strips unused imports — add an import in the same edit that uses it.
- Isolate global state in tests with `ANY2MD_CONFIG` / `ANY2MD_STATS` → tmp paths.
- The #1–#7 warnings backbone is untouched (warnings stay terminal-only, never rendered).
