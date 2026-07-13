"""Entry point for the tabulaflow CLI."""

import typer

from tabulaflow.app.config import LLMPreset

app = typer.Typer(
    name="tabulaflow",
    help="Minimalist Text-to-Query toolkit — interactive SQL / Cypher chat.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _resolve_startup_llm_preset(*, llm_preset: str | None) -> LLMPreset | None:
    from tabulaflow.app.config import load_app_config, resolve_startup_llm_preset

    try:
        return resolve_startup_llm_preset(load_app_config(), cli_preset=llm_preset)
    except ValueError as e:
        raise typer.BadParameter(str(e), param_hint="--llm-preset") from None


@app.command()
def chat(
    llm_preset: str | None = typer.Option(
        None,
        "--llm-preset",
        "-p",
        help="LLM preset label to use for this launch. Overrides the saved active preset without persisting.",
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

    startup_llm_preset = _resolve_startup_llm_preset(llm_preset=llm_preset)

    tabulaflow.configure(
        column_stats_mode="always_skip",
        query_cache_enabled=False,
        instrument_enabled=False,
        log_level="WARNING",
    )

    from tabulaflow.app.tui import run_tui

    asyncio.run(
        run_tui(
            llm_preset=startup_llm_preset,
            output_pane_host=output_pane_host,
            output_pane_port=output_pane_port,
            output_pane_public_url=output_pane_public_url,
        )
    )


def main() -> None:
    app()
