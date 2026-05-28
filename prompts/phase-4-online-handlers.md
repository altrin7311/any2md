# Phase 4 — Online handlers (YouTube, Reddit, GitHub, Web)

## Context
Add the four URL handlers. Read `.claude/rules/handler-contract.md`, `output-format.md`,
`testing.md`, and the `add-source-handler` skill. Depends on Phases 2–3.
**Build each handler TDD-first against a saved fixture — no live network in tests.**

Consider dispatching the `handler-builder` subagent per handler (isolated, token-cheap).

## Goal
`any2md convert <url>` works for YouTube, Reddit, GitHub, and arbitrary articles, each
producing correct frontmatter (incl. `source_url`, `upload_date`) + summary.

## Build (one Handler each, registered before the `web` fallback)
1. `youtube.py` — `yt-dlp`: title, channel, `upload_date`, description, captions →
   `body_markdown` (transcript). Whisper fallback only if `whisper_fallback=true` AND no
   captions; off by default. metadata: channel, duration, video_id.
2. `reddit.py` — public `<thread>.json` via `httpx`. Post body + top 20 comments by score,
   nested. metadata: subreddit, author, score, upload_date.
3. `github.py` — public REST (unauthenticated): README (decoded) + repo metadata
   (stars, topics, license, languages, description, created/updated dates).
4. `web.py` — `trafilatura` readability extraction. CATCH-ALL fallback: `matches()` returns
   true for any http(s) URL not claimed by a specialized handler. Must be registered LAST.
   metadata: site, author, published date if detectable.

## TDD
- Per handler: a recorded fixture in `tests/fixtures/` + `tests/test_<source>.py` asserting
  `Document` fields. Replay the fixture; never hit the network.
- `tests/test_registry.py`: URL routing — youtube/reddit/github URLs hit their handler;
  a random article URL falls through to `web`.

## Done when
- `pytest -q` green; `ruff check .` clean.
- Live smoke (manual, network on): convert one real YouTube link, one Reddit thread, one
  GitHub repo, one article URL — each yields a sensible `.md`.

## Stop
Show one `.md` per source. Wait for manual testing before Phase 5.
