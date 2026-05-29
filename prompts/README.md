# Any2MD — Implementation Phase Prompts

Execute in order. Each phase is independently testable — **stop and test after each one**
before starting the next. Start a phase with `/phase <n>` or paste its prompt into a fresh chat.

Source of truth: `docs/superpowers/specs/2026-05-28-any2md-design.md`
Contracts & conventions: `.claude/rules/`

| Phase | File | Builds | You can test |
|---|---|---|---|
| 0 | `phase-0-scaffold.md` | Package, deps, Typer CLI shell, config stubs | `any2md --help`, `any2md config set output X` persists |
| 1 | `phase-1-core-domain.md` | `Document`, `render()`, `writer`, `config` | Render a hand-built Document → `.md` file; unit tests green |
| 2 | `phase-2-files-pipeline.md` | Registry, `Handler` base, files handler, pipeline e2e | `any2md convert sample.pdf` → `.md` with frontmatter |
| 3 | `phase-3-enrichment.md` | `Summarizer` ABC, extractive (default) + ollama, enricher | Default convert adds summary/tags/wikilinks (zero setup); `none` = extraction-only |
| 4 | `phase-4-online-handlers.md` | youtube, reddit, github, web handlers | `any2md convert <youtube/reddit/github/article url>` |
| 5 | `phase-5-queue-repl.md` | Async queue, REPL slash-commands, progress, batch | `any2md` REPL: paste links, `/output`, `/jobs`, `/batch` |
| 6 | `phase-6-serve-docker-railway.md` | FastAPI serve, Dockerfile, railway.toml, token auth | `docker build`, `serve` + curl, deploy to Railway |

## Rules every phase obeys
- TDD: write the failing test first (`.claude/rules/testing.md`).
- Honor hard constraints in `CLAUDE.md` (free/OSS, never hard-fail on missing LLM key,
  keys via env only, flat slugified output with required frontmatter).
- Build only the current phase's scope. No work from later phases.
- Finish with the phase's "Done when" checks, then stop for manual testing.
