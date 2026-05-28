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
        typer.echo("REPL not implemented yet")


@app.command()
def convert(
    target: str = typer.Argument(None, help="File path or URL to convert."),
    output: str = typer.Option(None, "-o", "--output", help="Output folder."),
    batch: str = typer.Option(None, "--batch", help="File of targets, one per line."),
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
    provider = config.get("provider")
    for item in targets:
        path = pipeline.convert(item, out, provider)
        typer.echo(f"wrote {path}")


@app.command()
def serve(port: int = typer.Option(8000, "--port", help="Port to serve on.")) -> None:
    """Run the HTTP server (for Docker/Railway)."""
    typer.echo("not implemented yet")


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
