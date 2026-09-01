"""Top-level command-line composition root."""

import typer

from tabulaflow.app.main import chat
from tabulaflow.research.cli import benchmark_app

app = typer.Typer(
    name="tabulaflow",
    help="Minimalist Text-to-Query toolkit.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.command()(chat)
app.add_typer(benchmark_app, name="benchmark")


def main() -> None:
    app()


__all__ = ["app", "main"]
