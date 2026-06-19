"""Command-line entry point.

``corpus-rag ingest`` resolves every configured source (``CORPUS_SOURCES``) via
the adapter registry and reports what was discovered. The indexing pipeline that
converts/embeds/writes these sources is wired in a subsequent step; this command
already owns source resolution and the ``--reset`` dev-reset flag.
"""

from __future__ import annotations

from pathlib import Path

import typer

from corpus_rag.adapters import discover_all
from corpus_rag.adapters.base import Source
from corpus_rag.settings import get_settings

app = typer.Typer(help="Corpus RAG Explorer CLI.", no_args_is_help=True)


def _label(source: Source) -> str:
    """Human-readable label for a discovered source."""
    if isinstance(source, str | Path):
        return str(source)
    # ByteStream — show its provenance / mime type.
    url = source.meta.get("source_url") if source.meta else None
    return url or f"<bytes {source.mime_type or 'unknown'}>"


@app.command()
def ingest(
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Dev reset: recreate the vector table before ingesting.",
    ),
) -> None:
    """Discover all configured sources and (later) index them."""
    settings = get_settings()
    if not settings.corpus_sources:
        typer.echo("No CORPUS_SOURCES configured; nothing to ingest.")
        raise typer.Exit(code=1)

    sources = discover_all(settings.corpus_sources)
    typer.echo(f"Discovered {len(sources)} source(s):")
    for source in sources:
        typer.echo(f"  - {_label(source)}")

    if reset:
        typer.echo("--reset requested: table will be recreated at index time.")


if __name__ == "__main__":
    app()
