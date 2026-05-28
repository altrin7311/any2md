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
source_type: youtube        # youtube|reddit|github|web|pdf|docx|...
extraction_date: 2026-05-28  # ISO date, always present
upload_date: 2026-05-01      # ISO date or omitted if source has none
tags: [ai, tutorial]         # from enricher; [] if no LLM
---
```
- Type-specific metadata gets lifted into frontmatter when present, e.g. `channel`,
  `stars`, `subreddit`, `author`, `license`, `languages`.
- Omit a key entirely rather than writing `null`.

## Body layout
```markdown
# <title>

> **Summary:** <one concise summary>      # omitted when provider=none

Key concepts: [[Entity A]], [[Entity B]]   # wikilinks; omitted when none

## <Transcript | Content | Comments | README>
<extracted body_markdown>
```
- `#tags` live in frontmatter; `[[wikilinks]]` live inline in the body (Obsidian links).
- Keep the original extracted content intact below the summary — summary augments, never replaces.

`render()` is golden-file tested: a fixed `Document` must produce byte-exact expected `.md`.
