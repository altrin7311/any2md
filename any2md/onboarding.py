"""First-run onboarding — ask the output directory once; everything else auto-detected.

The user is asked exactly one thing: where to write .md files. The summarizer is chosen
silently (local Ollama if it's running, otherwise the zero-setup extractive default).
"""

from any2md import config
from any2md.enrich import ollama


def apply_first_run(output_dir: str) -> str:
    """Persist the chosen output dir and auto-pick a provider. Returns the provider name."""
    config.set_value("output_dir", output_dir)
    provider = "ollama" if ollama.available() else "extractive"
    config.set_value("provider", provider)
    return provider
