"""Command-line access to bundled examples."""

import asyncio
from collections.abc import Callable, Coroutine
from enum import Enum
import importlib
from typing import Any, Protocol, cast

import typer

from tabulaflow.research.benchmarks.installation import BenchmarkInstallationError


class ExampleName(str, Enum):
    AMBIGUITY_AWARE_QUERIES = "ambiguity-aware-queries"
    CHAT_SESSIONS = "chat-sessions"
    COMPARE_RESEARCH_AGENTS = "compare-research-agents"
    CUSTOM_AGENTS = "custom-agents"
    DATA_ENRICHMENT = "data-enrichment"
    DOCUMENT_EXTRACTION = "document-extraction"
    QUICK_START = "quick-start"
    RESEARCH_QUICK_START = "research-quick-start"
    STRUCTURED_OUTPUTS = "structured-outputs"
    TABLE_LINKING_AGENT = "table-linking-agent"
    WORKING_WITH_DATA = "working-with-data"


class ExampleModule(Protocol):
    main: Callable[[], Coroutine[Any, Any, None]]


examples_app = typer.Typer(
    help="Run examples bundled with this TabulaFlow installation.",
    no_args_is_help=True,
    add_completion=False,
)


@examples_app.command("list")
def list_examples() -> None:
    """List available examples."""
    for example in ExampleName:
        typer.echo(example.value)


@examples_app.command("run")
def run_example(example: ExampleName) -> None:
    """Run an example by name."""
    module_name = example.value.replace("-", "_")
    module = cast(ExampleModule, importlib.import_module(f"tabulaflow.examples.{module_name}"))
    try:
        asyncio.run(module.main())
    except BenchmarkInstallationError as error:
        typer.echo(f"Setup required: {error}", err=True)
        raise typer.Exit(1) from None


__all__ = ["ExampleName", "examples_app"]
