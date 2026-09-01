"""Top-level command-line composition root."""

import typer

from tabulaflow.app.main import AppServiceTier, run_chat
from tabulaflow.research.cli import benchmark_app

app = typer.Typer(
    name="tabulaflow",
    help="Minimalist Text-to-Query toolkit.",
    no_args_is_help=False,
    rich_markup_mode="rich",
)
app.add_typer(benchmark_app, name="benchmark")


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    llm_preset: str | None = typer.Option(
        None,
        "--llm-preset",
        "-p",
        help="LLM preset label or 'off' for this launch. Overrides the saved selection without persisting.",
    ),
    service_tier: AppServiceTier = typer.Option(
        AppServiceTier.DEFAULT,
        "--service-tier",
        help="LLM request service tier for this launch. Priority may incur premium API pricing.",
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
    """Start an interactive chat by default or run a subcommand."""
    if ctx.invoked_subcommand is None:
        run_chat(
            llm_preset=llm_preset,
            service_tier=service_tier,
            output_pane_port=output_pane_port,
            output_pane_host=output_pane_host,
            output_pane_public_url=output_pane_public_url,
        )


def main() -> None:
    app()


__all__ = ["app", "main"]
