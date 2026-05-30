# Graph Report - .  (2026-05-30)

## Corpus Check
- Corpus is ~40,922 words - fits in a single context window. You may not need a graph.

## Summary
- 1026 nodes · 1948 edges · 71 communities (51 shown, 20 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 221 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_REPL & Theme UI|REPL & Theme UI]]
- [[_COMMUNITY_Pipeline & E2E Tests|Pipeline & E2E Tests]]
- [[_COMMUNITY_Project Docs & Deployment|Project Docs & Deployment]]
- [[_COMMUNITY_Config & Polish Tests|Config & Polish Tests]]
- [[_COMMUNITY_YouTube Handler|YouTube Handler]]
- [[_COMMUNITY_URL Canonicalize & Depth|URL Canonicalize & Depth]]
- [[_COMMUNITY_Reddit Handler|Reddit Handler]]
- [[_COMMUNITY_Web Handler|Web Handler]]
- [[_COMMUNITY_REPL Command Tests|REPL Command Tests]]
- [[_COMMUNITY_Build Phase Sequence|Build Phase Sequence]]
- [[_COMMUNITY_Enricher Tests|Enricher Tests]]
- [[_COMMUNITY_Registry & Extractive Tests|Registry & Extractive Tests]]
- [[_COMMUNITY_Config Management|Config Management]]
- [[_COMMUNITY_Writer (SlugRename)|Writer (Slug/Rename)]]
- [[_COMMUNITY_Online Handlers Cluster|Online Handlers Cluster]]
- [[_COMMUNITY_Render & Frontmatter|Render & Frontmatter]]
- [[_COMMUNITY_ETA Estimation|ETA Estimation]]
- [[_COMMUNITY_CLI Commands|CLI Commands]]
- [[_COMMUNITY_GitHub Handler|GitHub Handler]]
- [[_COMMUNITY_Summarizer Providers|Summarizer Providers]]
- [[_COMMUNITY_Document & Extract API|Document & Extract API]]
- [[_COMMUNITY_Files Handler (markitdown)|Files Handler (markitdown)]]
- [[_COMMUNITY_Job Queue Internals|Job Queue Internals]]
- [[_COMMUNITY_Extractive Summarizer|Extractive Summarizer]]
- [[_COMMUNITY_Extractive Quality Tests|Extractive Quality Tests]]
- [[_COMMUNITY_Summarizer ABC & Ollama|Summarizer ABC & Ollama]]
- [[_COMMUNITY_Queue Tests|Queue Tests]]
- [[_COMMUNITY_Server Auth Tests|Server Auth Tests]]
- [[_COMMUNITY_HN Comments Fixture|HN Comments Fixture]]
- [[_COMMUNITY_CLI Tests|CLI Tests]]
- [[_COMMUNITY_Handler ABC Contract|Handler ABC Contract]]
- [[_COMMUNITY_Tweet Fixture|Tweet Fixture]]
- [[_COMMUNITY_Enricher & Tag Normalize|Enricher & Tag Normalize]]
- [[_COMMUNITY_Stack Overflow Handler|Stack Overflow Handler]]
- [[_COMMUNITY_Extractive Tag Summarizer|Extractive Tag Summarizer]]
- [[_COMMUNITY_HN Story Fixture|HN Story Fixture]]
- [[_COMMUNITY_Hacker News Handler|Hacker News Handler]]
- [[_COMMUNITY_Twitter Handler|Twitter Handler]]
- [[_COMMUNITY_Wikipedia Fixture|Wikipedia Fixture]]
- [[_COMMUNITY_Config Tests|Config Tests]]
- [[_COMMUNITY_FastAPI Server|FastAPI Server]]
- [[_COMMUNITY_GitHub Repo Fixture|GitHub Repo Fixture]]
- [[_COMMUNITY_Wikipedia Handler|Wikipedia Handler]]
- [[_COMMUNITY_Claude Hooks Config|Claude Hooks Config]]
- [[_COMMUNITY_TextRank+MMR Internals|TextRank+MMR Internals]]
- [[_COMMUNITY_New Handlers Test Group|New Handlers Test Group]]
- [[_COMMUNITY_Queue Converter Glue|Queue Converter Glue]]
- [[_COMMUNITY_HN Handler + Fixtures|HN Handler + Fixtures]]
- [[_COMMUNITY_SO Handler + Fixtures|SO Handler + Fixtures]]
- [[_COMMUNITY_GitHub Languages Fixture|GitHub Languages Fixture]]
- [[_COMMUNITY_Output Format Rules|Output Format Rules]]
- [[_COMMUNITY_Package Entry|Package Entry]]
- [[_COMMUNITY_Ruff Hook Script|Ruff Hook Script]]
- [[_COMMUNITY_GitHub README Fixture|GitHub README Fixture]]
- [[_COMMUNITY_SO Answers Fixture|SO Answers Fixture]]
- [[_COMMUNITY_SO Question Fixture|SO Question Fixture]]
- [[_COMMUNITY_Wikipedia Handler + Fixture|Wikipedia Handler + Fixture]]
- [[_COMMUNITY_Twitter Handler + Fixture|Twitter Handler + Fixture]]
- [[_COMMUNITY_Core Constraints|Core Constraints]]
- [[_COMMUNITY_URL Dedup Design|URL Dedup Design]]
- [[_COMMUNITY_Best-Effort Enrichment|Best-Effort Enrichment]]
- [[_COMMUNITY_Async Queue Concept|Async Queue Concept]]
- [[_COMMUNITY_Wikilink Inlining|Wikilink Inlining]]
- [[_COMMUNITY_Extractive Quality Goal|Extractive Quality Goal]]
- [[_COMMUNITY_Skip Empty Extractions|Skip Empty Extractions]]
- [[_COMMUNITY_Valid Obsidian Tags|Valid Obsidian Tags]]
- [[_COMMUNITY_Single Warnings Channel|Single Warnings Channel]]
- [[_COMMUNITY_Ollama Fallback Warning|Ollama Fallback Warning]]

## God Nodes (most connected - your core abstractions)
1. `Document` - 102 edges
2. `JobQueue` - 48 edges
3. `convert()` - 40 edges
4. `Summarizer` - 36 edges
5. `Handler` - 29 edges
6. `Repl` - 28 edges
7. `YouTubeHandler` - 27 edges
8. `RedditHandler` - 27 edges
9. `WebHandler` - 25 edges
10. `_repl()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `FastAPI Server` --semantically_similar_to--> `Repl`  [INFERRED] [semantically similar]
  prompts/phase-6-serve-docker-railway.md → any2md/repl.py
- `Tech stack & tooling rule` --references--> `FilesHandler`  [INFERRED]
  .claude/rules/tech-stack.md → any2md/handlers/files.py
- `Output format rule (Obsidian Markdown)` --references--> `Document dataclass`  [INFERRED]
  .claude/rules/output-format.md → any2md/models.py
- `Phase 1 — Core Domain` --references--> `Document`  [INFERRED]
  prompts/phase-1-core-domain.md → any2md/models.py
- `Golden Full Render` --references--> `render()`  [INFERRED]
  tests/fixtures/golden_full.md → any2md/render.py

## Hyperedges (group relationships)
- **Conversion pipeline: detect to extract to enrich to render to write** — any2md_pipeline_convert, any2md_registry_detect, enrich_enricher_enrich_with_fallback, any2md_render_render, any2md_writer_write [EXTRACTED 0.95]
- **Pluggable summarizer strategy (extractive/ollama/none)** — enrich_base_summarizer, extractive_extractive_extractivesummarizer, enrich_ollama_ollamasummarizer, enrich_providers_get_summarizer [EXTRACTED 0.90]
- **One async queue, two front-ends (REPL + serve)** — any2md_queue_jobqueue, any2md_repl_repl, any2md_server_create_app [INFERRED 0.85]
- **Handlers implementing the Handler ABC** — handlers_base_handler, handlers_files_fileshandler, handlers_hackernews_hackernewshandler, handlers_web_webhandler, handlers_youtube_youtubehandler, handlers_arxiv_arxivhandler, handlers_twitter_twitterhandler, handlers_stackoverflow_stackoverflowhandler, handlers_github_githubhandler, handlers_reddit_reddithandler, handlers_wikipedia_wikipediahandler [EXTRACTED 1.00]
- **Handlers producing the shared Document contract** — models_document, handlers_files_fileshandler, handlers_youtube_youtubehandler, handlers_reddit_reddithandler, handlers_github_githubhandler, handlers_web_webhandler [EXTRACTED 1.00]
- **Keyless httpx-fetching URL handlers** — handlers_hackernews_hackernewshandler, handlers_arxiv_arxivhandler, handlers_twitter_twitterhandler, handlers_stackoverflow_stackoverflowhandler, handlers_github_githubhandler, handlers_reddit_reddithandler, handlers_wikipedia_wikipediahandler [INFERRED 0.85]
- **End-to-end full pipeline coverage** — tests_test_e2e_all, tests_test_e2e_files, tests_test_pipeline, any2md_pipeline_convert [INFERRED 0.85]
- **Per-source handler extraction tests** — tests_test_youtube, tests_test_reddit, tests_test_github, tests_test_web, tests_test_new_handlers, tests_test_files_handler [INFERRED 0.80]
- **Shared queue front-end tests** — tests_test_queue, tests_test_repl, tests_test_server, any2md_queue_jobqueue [INFERRED 0.80]
- **Any2MD Implementation Phase Sequence** — prompts_phase_0_scaffold_phase, prompts_phase_1_core_domain_phase, prompts_phase_2_files_pipeline_phase, prompts_phase_3_enrichment_phase, prompts_phase_4_online_handlers_phase, prompts_phase_5_queue_repl_phase, prompts_phase_6_serve_docker_railway_phase [EXTRACTED 1.00]
- **Recorded Source Response Fixtures** — fixtures_reddit_post_fixture, fixtures_tweet_result_fixture, fixtures_stackoverflow_question_fixture, fixtures_github_repo_fixture, fixtures_hn_story_fixture, fixtures_wikipedia_summary_fixture [INFERRED 0.85]
- **Add-a-Source Workflow** — add_source_handler_skill, commands_new_handler, agents_handler_builder, add_source_handler_handler_contract [EXTRACTED 1.00]
- **CI to Production Deploy Flow** — ci_pipeline, ci_ruff_check, ci_pytest, deploy_railway, deploy_dockerfile [EXTRACTED 1.00]
- **Ruff Lint Quality Gate** — hooks_ruff_script, settings_ruff_posttooluse_hook, ci_ruff_check, commands_checks [INFERRED 0.85]

## Communities (71 total, 20 thin omitted)

### Community 0 - "REPL & Theme UI"
Cohesion: 0.05
Nodes (63): _clean_dropped_path(), display_name(), _looks_convertible(), _make_auto_suggest(), _make_keybindings(), _make_lexer(), _opener_cmd(), bool (+55 more)

### Community 1 - "Pipeline & E2E Tests"
Cohesion: 0.08
Nodes (46): cli app, pipeline module, convert(), is_low_content(), pipeline order (detect to extract to enrich to render to write), bool, Path, str (+38 more)

### Community 2 - "Project Docs & Deployment"
Cohesion: 0.08
Nodes (43): Handler/Document Contract, add-source-handler skill, handler-builder agent, Bug Report Issue Template, CI Pipeline (GitHub Actions), pytest -q (test suite), ruff check . (lint), CLAUDE.md Working Contract (+35 more)

### Community 3 - "Config & Polish Tests"
Cohesion: 0.05
Nodes (26): config module, depth module, eta module, GitHubHandler, RedditHandler, WebHandler, YouTubeHandler, onboarding module (+18 more)

### Community 4 - "YouTube Handler"
Cohesion: 0.09
Nodes (31): bool, Document, str, _get_captions(), _parse_vtt(), Strip VTT timestamps/headers → plain transcript text., Thin yt-dlp wrapper — isolated for mocking in tests., Try to fetch English captions from VTT URL in yt-dlp info dict. (+23 more)

### Community 5 - "URL Canonicalize & Depth"
Cohesion: 0.09
Nodes (29): is_raw(), next_level(), prev_level(), bool, float, str, ratio(), Summary depth: how much of a source to keep. low/medium/high → fraction of the s (+21 more)

### Community 6 - "Reddit Handler"
Cohesion: 0.13
Nodes (26): bool, Document, int, str, _extract_json(), _extract_rss(), _fetch_json(), _fetch_rss() (+18 more)

### Community 7 - "Web Handler"
Cohesion: 0.12
Nodes (26): bool, Document, str, _clean_title(), _fetch_and_extract(), Web handler — trafilatura readability extraction. Catch-all for any http(s) URL., Fetch and extract article content — isolated for mocking in tests., Recover a title from raw HTML: the <title> tag, else the first <h1>. (+18 more)

### Community 8 - "REPL Command Tests"
Cohesion: 0.13
Nodes (27): Pull the TL;DR text out of a rendered note so the REPL can show a one-glance pre, tldr_peek(), REPL command-handling tests — submissions + config mutations, no real conversion, _repl(), test_batch_command_submits_each_line(), test_depth_command_accepts_raw(), test_depth_command_rejects_bad_level(), test_depth_command_sets_and_persists() (+19 more)

### Community 9 - "Build Phase Sequence"
Cohesion: 0.08
Nodes (29): Typer CLI, config, pipeline.convert, Async Queue, registry, FastAPI Server, writer, Summarizer ABC (+21 more)

### Community 10 - "Enricher Tests"
Cohesion: 0.16
Nodes (28): bool, Summarizer, enrich(), inline_links(), Wrap the first bare whole-word occurrence of each phrase with [[ ]] (Obsidian li, Distill the doc into TL;DR + key points (with [[links]] inlined) at the given de, _Boom, _doc() (+20 more)

### Community 11 - "Registry & Extractive Tests"
Cohesion: 0.10
Nodes (27): enrich, inline_links, normalize_tag, ExtractiveSummarizer, OllamaSummarizer, get_summarizer, FilesHandler, registry module (+19 more)

### Community 12 - "Config Management"
Cohesion: 0.13
Nodes (25): cli._root, _canonical(), _coerce(), config_path(), effective(), get(), is_first_run(), config precedence (env > toml > default) (+17 more)

### Community 13 - "Writer (Slug/Rename)"
Cohesion: 0.16
Nodes (24): Repl._rename, writer module, _find_by_source_url(), Document, Path, str, Slugify a Document's title and write its rendered Markdown to the output folder., The existing note for this source_url, if any — so re-converting refreshes one n (+16 more)

### Community 14 - "Online Handlers Cluster"
Cohesion: 0.19
Nodes (23): Handler, str, Pick the right handler for a target. Specialized handlers first; `web` catch-all, Handler, ArxivHandler, HackerNewsHandler, StackOverflowHandler, TwitterHandler (+15 more)

### Community 15 - "Render & Frontmatter"
Cohesion: 0.15
Nodes (21): render module, render._frontmatter, distilled note vs passthrough rendering, _format_meta(), _frontmatter(), Document, object, str (+13 more)

### Community 16 - "ETA Estimation"
Cohesion: 0.16
Nodes (21): classify(), EMA-based learned ETA, estimate(), estimate_lines(), _load(), float, int, Path (+13 more)

### Community 17 - "CLI Commands"
Cohesion: 0.11
Nodes (20): cli._warn_collector, config_set(), config_show(), convert(), main(), bool, int, str (+12 more)

### Community 18 - "GitHub Handler"
Cohesion: 0.19
Nodes (16): bool, Document, str, _fetch_languages(), _fetch_readme(), _fetch_repo(), GitHubHandler, GitHub handler — public REST API (unauthenticated, 60 req/hr). (+8 more)

### Community 19 - "Summarizer Providers"
Cohesion: 0.14
Nodes (14): str, Summarizer, OllamaSummarizer, get_summarizer(), Resolve a summarizer name into a Summarizer (or None for extraction-only). No AP, None = "no enrichment" (extraction-only). Never errors for the `none` case., test_get_summarizer_extractive_is_default_capable(), test_get_summarizer_none_returns_none() (+6 more)

### Community 20 - "Document & Extract API"
Cohesion: 0.14
Nodes (12): bool, Document, str, bool, Document, str, Document, The internal normalized document every handler produces and the renderer consume (+4 more)

### Community 21 - "Files Handler (markitdown)"
Cohesion: 0.13
Nodes (8): MarkItDown.convert (files), FilesHandler, Local-file handler: wraps markitdown to convert pdf/docx/pptx/xlsx/csv/html/..., Structured/tiny source passthrough, _FakeResult, test_image_with_tesseract_extracts_and_no_warning(), test_image_without_tesseract_warns_and_degrades(), test_non_image_conversion_error_propagates()

### Community 22 - "Job Queue Internals"
Cohesion: 0.18
Nodes (8): Job, JobQueue, int, str, Await until the job reaches a terminal state (done | error)., test_queue, test_repl, test_server

### Community 23 - "Extractive Summarizer"
Cohesion: 0.27
Nodes (16): float, str, _clean_prose(), _content(), _key_phrases(), Pure-Python extractive summarizer. No model, no network, no deps — works everywh, Strip markdown structure (tables, headings, lists, code, nav, boilerplate, URLs), Classic TextRank overlap, normalized by sentence lengths. (+8 more)

### Community 24 - "Extractive Quality Tests"
Cohesion: 0.22
Nodes (17): Quality tests for the extractive summarizer (TextRank + cleaning + MMR + % depth, All distilled prose: TL;DR plus every key point., _summ(), test_captures_the_thesis(), test_concepts_drop_language_names(), test_concepts_drop_table_nav_and_title(), test_drops_list_and_table_artifacts(), test_empty_body_is_safe() (+9 more)

### Community 25 - "Summarizer ABC & Ollama"
Cohesion: 0.15
Nodes (11): float, str, bool, float, str, Summarizer contract: produce knowledge-graph metadata from text. No APIs, no key, Distill to ~ratio of the source. Return         {"tldr": str, "key_points": list, Summarizer (+3 more)

### Community 26 - "Queue Tests"
Cohesion: 0.33
Nodes (11): _drain(), JobQueue, Async job queue tests — fake converter, no real conversions., _run(), test_queue_all_lists_every_job(), test_queue_captures_per_job_error_without_killing_others(), test_queue_emits_ordered_progress_events(), test_queue_marks_job_skipped_when_nothing_written() (+3 more)

### Community 27 - "Server Auth Tests"
Cohesion: 0.24
Nodes (14): server module, _client(), _make_convert(), HTTP serve-mode tests — FastAPI TestClient, fake converter, no real conversions., test_auth_accepts_correct_token(), test_auth_open_when_no_token(), test_auth_rejects_missing_token(), test_convert_returns_job_id() (+6 more)

### Community 28 - "HN Comments Fixture"
Cohesion: 0.13
Nodes (14): 101, by, id, kids, text, time, type, 102 (+6 more)

### Community 30 - "Handler ABC Contract"
Cohesion: 0.15
Nodes (12): ABC, bool, Document, str, Handler, The Handler contract: one per source, extraction only (see .claude/rules/handler, Cheap, side-effect-free check: does this handler claim the target?, Fetch/parse the target into a Document. No LLM calls, no file writing. (+4 more)

### Community 31 - "Tweet Fixture"
Cohesion: 0.15
Nodes (12): conversation_count, created_at, favorite_count, id_str, lang, text, __typename, user (+4 more)

### Community 32 - "Enricher & Tag Normalize"
Cohesion: 0.19
Nodes (12): Document, float, str, best-effort enrichment (never hard-fail), enrich_with_fallback(), normalize_tag(), _normalize_tags(), Enrich a Document with a summary, tags, and wikilinks via a Summarizer.  Best-ef (+4 more)

### Community 33 - "Stack Overflow Handler"
Cohesion: 0.21
Nodes (10): bool, Document, int, str, _fetch_answers(), _fetch_question(), Stack Overflow handler — public Stack Exchange API, keyless. Question + top answ, Fetch the question (with body) — isolated for mocking. (+2 more)

### Community 34 - "Extractive Tag Summarizer"
Cohesion: 0.30
Nodes (9): ExtractiveSummarizer, Summarizer, float, str, _SpacedTagSummarizer, test_extractive_concepts_drop_bare_stopwords(), test_extractive_drops_spoken_filler_from_tags(), test_extractive_empty_body_is_safe() (+1 more)

### Community 35 - "HN Story Fixture"
Cohesion: 0.18
Nodes (10): by, descendants, id, kids, score, text, time, title (+2 more)

### Community 36 - "Hacker News Handler"
Cohesion: 0.22
Nodes (8): bool, Document, int, str, _fetch_item(), Hacker News handler — public Firebase API, keyless. Story + top comments., Fetch one HN item (story or comment) — isolated for mocking., _strip_html()

### Community 37 - "Twitter Handler"
Cohesion: 0.24
Nodes (8): bool, Document, str, _fetch_tweet(), Twitter/X handler — keyless syndication CDN (cdn.syndication.twimg.com).  X bloc, Reproduce the token the embed widget derives from the tweet id., Fetch the syndication tweet record — isolated for mocking., _syndication_token()

### Community 38 - "Wikipedia Fixture"
Cohesion: 0.20
Nodes (9): content_urls, desktop, description, page, extract, lang, timestamp, title (+1 more)

### Community 40 - "FastAPI Server"
Cohesion: 0.25
Nodes (8): queue module, ConvertRequest, create_app(), JobQueue, str, FastAPI serve mode — same pipeline + queue over HTTP. For Docker / Railway.  Aut, BaseModel, FastAPI

### Community 41 - "GitHub Repo Fixture"
Cohesion: 0.22
Nodes (8): created_at, description, full_name, license, spdx_id, stargazers_count, topics, updated_at

### Community 42 - "Wikipedia Handler"
Cohesion: 0.25
Nodes (6): bool, Document, str, _fetch_summary(), Wikipedia handler — public REST summary API, keyless., Fetch the REST page summary — isolated for mocking.

### Community 43 - "Claude Hooks Config"
Cohesion: 0.33
Nodes (5): hooks, PostToolUse, PreToolUse, permissions, allow

### Community 44 - "TextRank+MMR Internals"
Cohesion: 0.33
Nodes (6): extractive._clean_prose, extractive._key_phrases, extractive._select, extractive._textrank, ExtractiveSummarizer, TextRank + MMR extractive summarization

### Community 45 - "New Handlers Test Group"
Cohesion: 0.33
Nodes (6): ArxivHandler, HackerNewsHandler, StackOverflowHandler, TwitterHandler, WikipediaHandler, test_new_handlers

### Community 46 - "Queue Converter Glue"
Cohesion: 0.50
Nodes (3): _default_convert(), Async job queue — shared engine for the REPL and `serve`.  Submit a target → job, Real converter: the pipeline, reporting stages via on_event.

### Community 47 - "HN Handler + Fixtures"
Cohesion: 0.67
Nodes (3): Hacker News Comments Fixture, Hacker News Story Fixture, Hacker News Handler

### Community 48 - "SO Handler + Fixtures"
Cohesion: 0.67
Nodes (3): Stack Overflow Answers Fixture, Stack Overflow Question Fixture, Stack Overflow Handler

### Community 50 - "Output Format Rules"
Cohesion: 0.67
Nodes (3): Output format rule (Obsidian Markdown), /depth command (low/medium/high ratio), Distilled note (summary replaces body)

## Knowledge Gaps
- **147 isolated node(s):** `int`, `Path`, `bool`, `bool`, `str` (+142 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Document` connect `Document & Extract API` to `Pipeline & E2E Tests`, `YouTube Handler`, `Reddit Handler`, `Web Handler`, `Build Phase Sequence`, `Enricher Tests`, `Registry & Extractive Tests`, `Writer (Slug/Rename)`, `Online Handlers Cluster`, `Render & Frontmatter`, `GitHub Handler`, `Files Handler (markitdown)`, `Handler ABC Contract`, `Enricher & Tag Normalize`, `Stack Overflow Handler`, `Extractive Tag Summarizer`, `Hacker News Handler`, `Twitter Handler`, `Wikipedia Handler`?**
  _High betweenness centrality (0.288) - this node is a cross-community bridge._
- **Why does `convert()` connect `Pipeline & E2E Tests` to `Enricher & Tag Normalize`, `URL Canonicalize & Depth`, `Registry & Extractive Tests`, `Config Management`, `Writer (Slug/Rename)`, `ETA Estimation`, `CLI Commands`?**
  _High betweenness centrality (0.250) - this node is a cross-community bridge._
- **Why does `convert()` connect `CLI Commands` to `REPL & Theme UI`, `Pipeline & E2E Tests`, `Job Queue Internals`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Are the 72 inferred relationships involving `Document` (e.g. with `bool` and `Document`) actually correct?**
  _`Document` has 72 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `JobQueue` (e.g. with `convert()` and `bool`) actually correct?**
  _`JobQueue` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `Summarizer` (e.g. with `bool` and `Document`) actually correct?**
  _`Summarizer` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Handler` (e.g. with `Document` and `Handler contract (matches + extract)`) actually correct?**
  _`Handler` has 2 INFERRED edges - model-reasoned connections that need verification._