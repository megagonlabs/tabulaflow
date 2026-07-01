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
    reasoning_effort: str = typer.Option(
        "medium",
        "--reasoning-effort",
        "-r",
        help="Reasoning effort for OpenAI models: minimal | low | medium | high.",
    ),
    output_pane_port: int | None = typer.Option(
        None,
        "--output-pane-port",
        help="Strict port for the browser output pane. Defaults to the first free port in 61111-61130.",
    ),
    output_pane_host: str = typer.Option(
        "127.0.0.1",
        "--output-pane-host",
        help="Bind host for the browser output pane.",
    ),
    output_pane_public_url: str | None = typer.Option(
        None,
        "--output-pane-public-url",
        help="Browser-facing base URL for the output pane. The session token is appended automatically.",
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

    asyncio.run(
        run_tui(
            model=model,
            agent=agent,
            reasoning_effort=reasoning_effort,
            output_pane_host=output_pane_host,
            output_pane_port=output_pane_port,
            output_pane_public_url=output_pane_public_url,
        )
    )


def main() -> None:
    app()
