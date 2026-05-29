# Rule: Output format (Obsidian Markdown)

Target vault: Karpathy-style Obsidian knowledge graph. One `.md` per converted source.

## Filename
- Flat in the configured output folder (no subfolders).
- Slugified from `title`: lowercase, spaces→`-`, strip non `[a-z0-9-]`, collapse repeats.
  Example: `"How to Build X!"` → `how-to-build-x.md`.
- Collision → append `-2`, `-3`, … : `how-to-build-x-2.md`.

## Frontmatter (YAML) — required keys
```yaml
---
title: "<title>"
source_url: "<url or omitted for local files>"
source_type: youtube        # youtube|reddit|github|hackernews|arxiv|wikipedia|stackoverflow|twitter|web|pdf|docx|...
extraction_date: 2026-05-28  # ISO date, always present
upload_date: 2026-05-01      # ISO date or omitted if source has none
tags: [ai, tutorial]         # from enricher; [] if no summarizer
---
```
- Type-specific metadata is lifted into frontmatter when present, in this order:
  `channel`, `stars`, `subreddit`, `author`, `handle`, `license`, `languages`, `authors`,
  `categories`, `score`, `comments`, `likes`, `lang`. (`tags` is reserved for the enricher line —
  never lift a metadata key named `tags`.)
- Omit a key entirely rather than writing `null`.

## Body layout — distilled knowledge note
The note **is** the summary: the distilled signal (the important ~N% of the source), not the
raw body. The summary REPLACES the body — it does not augment it. One unified layout for every
source (no per-source section headings):
```markdown
# <title>

> [!summary] TL;DR
> <mini multi-sentence summary, with [[wikilinks]] inlined>

## Key Points
- <high-signal point, [[wikilinks]] inlined>
- <…this list is the kept ~N% of the source>
```
- `#tags` live in frontmatter; `[[wikilinks]]` are **inlined** into the TL;DR + Key Points (first
  whole-word occurrence of each concept) — there is no separate "Concepts" section.
- **Depth** controls N via the `depth` config (low 10% · medium 20% · high 35% of the source),
  set with the REPL `/depth` picker, `--depth`, or `ANY2MD_DEPTH`. See `depth.py`.

## Passthrough (no distillation)
When there is nothing to distill — `provider=none`, or structured/empty sources (csv, xlsx,
json, xml, or near-empty prose) — the raw `body_markdown` passes through under a section heading
instead (youtube→Transcript, github→README, reddit→Thread, hackernews→Discussion,
stackoverflow→Question, arxiv→Abstract, wikipedia→Article, twitter→Tweet; default `Content`).
**If `body_markdown` already opens with its own `## ` heading, `render()` omits the auto heading.**

`render()` is golden-file tested: a fixed `Document` must produce byte-exact expected `.md`.
