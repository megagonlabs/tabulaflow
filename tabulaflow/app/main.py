"""Entry point for the tabulaflow CLI."""

import typer

app = typer.Typer(
    name="tabulaflow",
    help="Minimalist Text-to-Query toolkit — interactive SQL / Cypher chat.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.command()
def chat(
    model: str = typer.Option(
        "openai-responses:gpt-5.4",
        "--model",
        "-m",
        help="LLM identifier (e.g. openai-responses:gpt-5.4).",
    ),
    agent: str = typer.Option(
        "tabulaflow_agent",
        "--agent",
        "-a",
        help="Agent name from the tabulaflow agent registry.",
    ),
) -> None:
    """Start an interactive database chat session (SQL or Neo4j Cypher)."""
    import asyncio

    import tabulaflow

    tabulaflow.configure(
        column_stats_mode="always_skip",
        query_cache_enabled=False,
        instrument_enabled=False,
        log_level="WARNING",
    )

    from tabulaflow.app.tui import run_tui

    asyncio.run(run_tui(model=model, agent=agent))


def main() -> None:
    app()
