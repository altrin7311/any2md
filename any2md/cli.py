"""Any2MD command-line interface (Phase 0: shell + config; conversion lands later)."""

import typer

from any2md import __version__, config

app = typer.Typer(
    add_completion=False,
    help="Convert almost anything to Obsidian-flavored Markdown.",
    no_args_is_help=False,
)
config_app = typer.Typer(help="Read and write Any2MD configuration.")
app.add_typer(config_app, name="config")


def _warn_collector(sink: list):
    """An on_event callback that siphons 'warn:'-prefixed pipeline events into `sink`."""

    def on_event(stage: str) -> None:
        if stage.startswith("warn:"):
            sink.append(stage[len("warn:") :])

    return on_event


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    if ctx.invoked_subcommand is None:
        import asyncio

        from any2md.queue import JobQueue
        from any2md.repl import Repl

        repl = Repl(
            queue=JobQueue(),
            output_dir=str(config.get("output_dir")),
            provider=str(config.get("provider")),
        )
        asyncio.run(repl.run())


@app.command()
def convert(
    target: str = typer.Argument(None, help="File path or URL to convert."),
    output: str = typer.Option(None, "-o", "--output", help="Output folder."),
    batch: str = typer.Option(None, "--batch", help="File of targets, one per line."),
    depth: str = typer.Option(None, "--depth", help="Summary depth: low|medium|high."),
    provider: str = typer.Option(
        None, "--provider", help="Summarizer: extractive|ollama|none (overrides config)."
    ),
) -> None:
    """Convert a file or URL to Markdown."""
    from pathlib import Path

    from any2md import pipeline  # lazy: pulls markitdown, keep --help/config fast

    if batch:
        targets = [ln.strip() for ln in Path(batch).read_text().splitlines() if ln.strip()]
    elif target:
        targets = [target]
    else:
        typer.echo("provide a target or --batch FILE")
        raise typer.Exit(1)

    out = output or config.get("output_dir")
    provider = provider or config.get("provider")

    from rich.console import Console

    from any2md.theme import gradient_text

    console = Console()
    failures = 0
    for item in targets:
        warnings: list[str] = []
        try:
            path = pipeline.convert(
                item, out, provider, depth=depth, on_event=_warn_collector(warnings)
            )
        except Exception as exc:  # a flaky source must not crash the CLI (mirrors the queue)
            console.print(f"✗ {item}: {exc}", style="red")
            failures += 1
            continue
        if path is None:  # nothing written (empty / paywalled source) — surface why, not a ✓
            for warning in warnings:
                console.print(f"  ⚠ {warning}", style="#F59E0B")
            continue
        line = gradient_text("✓ wrote ", bold=True)
        line.append(str(path), style="dim")
        console.print(line)
        for warning in warnings:
            console.print(f"  ⚠ {warning}", style="#F59E0B")
    if failures:
        raise typer.Exit(1)


@app.command()
def serve(
    port: int = typer.Option(None, "--port", help="Port to serve on."),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind address."),
) -> None:
    """Run the HTTP server (for Docker/Railway)."""
    import uvicorn

    from any2md.server import create_app

    resolved_port = port if port is not None else int(os.environ.get("PORT", 8000))
    uvicorn.run(create_app(), host=host, port=resolved_port)


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    """Set a config value (e.g. `config set output ~/vault`)."""
    config.set_value(key, value)
    typer.echo(f"{key}={value}")


@config_app.command("show")
def config_show() -> None:
    """Show effective configuration."""
    for key, val in config.effective().items():
        typer.echo(f"{key}={val}")


def main() -> None:
    """Console-script entry point (a Typer instance is not directly callable)."""
    app()
