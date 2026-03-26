"""Entry point for the mintq CLI."""

import typer

app = typer.Typer(
    name="mintq",
    help="Minimalist Text-to-Query toolkit — interactive SQL chat.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.command()
def chat(
    model: str = typer.Option(
        "openai-responses:gpt-5-mini",
        "--model",
        "-m",
        help="LLM identifier (e.g. openai-responses:gpt-5-mini).",
    ),
    agent: str = typer.Option(
        "mintq_agent",
        "--agent",
        "-a",
        help="Agent name from the mintq agent registry.",
    ),
) -> None:
    """Start an interactive SQL chat session."""
    import asyncio

    from mintq.cli.chat import run_chat

    asyncio.run(run_chat(model=model, agent=agent))


def main() -> None:
    app()
