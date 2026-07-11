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
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM identifier (e.g. openai-responses:gpt-5.5). Overrides the saved default for this launch.",
    ),
    reasoning_effort: str | None = typer.Option(
        None,
        "--reasoning-effort",
        "-r",
        help="Reasoning effort: low | medium | high | xhigh. Overrides the saved default for this launch.",
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
    from typing import get_args

    from pydantic import ValidationError

    import tabulaflow
    from tabulaflow.app.config import ReasoningEffort, load_app_config

    app_config = load_app_config()
    if model is not None:
        app_config.model = model
    if reasoning_effort is not None:
        try:
            # CLI input is an arbitrary string; pydantic validates the literal on assignment.
            app_config.reasoning_effort = reasoning_effort  # type: ignore[assignment]
        except ValidationError:
            raise typer.BadParameter(
                f"{reasoning_effort!r} is not one of: {', '.join(get_args(ReasoningEffort))}",
                param_hint="--reasoning-effort",
            ) from None

    tabulaflow.configure(
        column_stats_mode="always_skip",
        query_cache_enabled=False,
        instrument_enabled=False,
        log_level="WARNING",
    )

    from tabulaflow.app.tui import run_tui

    asyncio.run(
        run_tui(
            model=app_config.model,
            reasoning_effort=app_config.reasoning_effort,
            output_pane_host=output_pane_host,
            output_pane_port=output_pane_port,
            output_pane_public_url=output_pane_public_url,
        )
    )


def main() -> None:
    app()
