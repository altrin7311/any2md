# Any2MD

> Free, open-source CLI that turns almost anything — local files and web links — into
> Obsidian-flavored Markdown for a Karpathy-style knowledge graph. **Every input is summarized.**

This file is the contract for working in this repo. Read the Orientation, follow the Working
Agreements, respect the Hard Constraints. When in doubt, the spec wins — then ask.

---

## Orientation — where things live

| You need… | Look here |
|---|---|
| The full design (source of truth) | `docs/superpowers/specs/2026-05-28-any2md-design.md` |
| Step-by-step build, phase by phase | `prompts/` (run `0→6`, test between each) |
| A contract or convention (don't re-read the whole spec) | `.claude/rules/` |
| To add a new source | skill `add-source-handler` · cmd `/new-handler` · agent `handler-builder` |

**`.claude/rules/` index** — load the one you need:
- `handler-contract.md` — the `Handler` ABC + the `Document` every layer passes around.
- `output-format.md` — exact frontmatter schema + filename/slug rules.
- `tech-stack.md` — pinned libraries, tools, env vars, config precedence.
- `testing.md` — TDD layout and the "no live network in tests" rule.

---

## Working Agreements
Behavioral guidelines to reduce common LLM coding mistakes.

- Whenever prompted for a summary, summarize the conversation into what is necessary — this
  information will be carried to a newer chat to save context. Write it as a `.md` file in the
  `summaries/` folder.
- Whenever an ambiguity is faced or a design question is raised, **ask me.**

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## The Project

### What it converts (MVP = Core 6)
- **Files** (one lib, `markitdown`): pdf, docx, pptx, xlsx, csv, images (OCR), html, epub.
- **YouTube** (`yt-dlp`): metadata + captions, plus a summary. Whisper fallback off by default.
- **Reddit**: post + top 20 comments by score, nested (public `.json`, no key).
- **GitHub**: README + repo metadata (stars / topics / license / languages / dates).
- **Web**: readability article extraction — the catch-all for any unmatched URL.

Later sources (Twitter/X, HN, Stack Overflow, Wikipedia, arXiv, podcasts…) are just new
`Handler`s — the architecture already accounts for them. Don't build them in the MVP.

### Architecture — Approach A: layered pipeline + handler registry
```
input → registry.detect() → handler.extract() → Document
      → enricher.enrich()  (summary / tags / wikilinks; skipped if no LLM)
      → render() → writer.write()        # flat, slugified .md in the output folder
```
- Each source = a small `Handler` (`matches` + `extract` → `Document`). Extraction only —
  no LLM calls, no file writing inside a handler.
- LLM sits behind an `LLMProvider` ABC, selected by config/env.
- One async `queue` is shared by the CLI REPL and the optional `serve` mode — one engine,
  two front-ends. Module map + exact contracts live in `.claude/rules/`.

### Interface
CLI, Claude-Code-style: an interactive **REPL** (`any2md` → paste links/paths, slash-commands
like `/output`, `/provider`, `/jobs`) **and** scriptable **one-shot** (`any2md convert <x> -o dir`).
Optional `any2md serve` exposes the same pipeline over HTTP for Docker / Railway.

### Tech stack
Python 3.11+ • Typer + Rich (CLI/REPL) • markitdown • yt-dlp • trafilatura • httpx •
FastAPI (serve) • pytest + ruff. Pluggable LLM: **Groq** (default) / Gemini / Cloudflare /
Ollama / `none`. Pins and env vars: `.claude/rules/tech-stack.md`.

### Hard Constraints (do not violate)
- **100% free / open-source.** No paid APIs, no paid hosting tier required.
- **Never hard-fail on a missing LLM key** — `provider=none` still does full extraction.
- **API keys come from env vars only** — never written to `config.toml`.
- **Output** is a flat, slugified `.md` with YAML frontmatter that always includes
  `source_url`, `source_type`, `extraction_date`, and `upload_date` when known.
  Schema: `.claude/rules/output-format.md`.
- **TDD per handler** against saved fixtures — no live network in tests
  (`.claude/rules/testing.md`).

---

## Project Commands
- `/phase <n>` — load and start a build phase from `prompts/` (stops at the phase boundary so you can test).
- `/new-handler <source>` — scaffold a new `Handler` + fixture test (TDD), via the `handler-builder` agent.
- `/checks` — run the test + lint suite (`ruff` + `pytest`).
