# Any2MD

Free, open-source CLI that converts almost anything — local files (PDF, DOCX, XLSX, images…)
and online links (YouTube, Reddit, GitHub, web articles) — into Obsidian-flavored Markdown
for a knowledge graph. Every input is summarized.

## Install (dev)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
any2md --help
any2md config set output ~/ObsidianVault/inbox
any2md config show
```

> Status: early scaffold. Conversion handlers land in later build phases (see `prompts/`).
