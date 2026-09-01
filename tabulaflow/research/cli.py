"""Command-line interface for research benchmarks."""

import asyncio

import httpx
import typer
from rich.console import Console
from rich.table import Table

from tabulaflow.research.benchmarks.installation import BenchmarkInstallationError
from tabulaflow.research.benchmarks.registry import dataset_registry

benchmark_app = typer.Typer(help="Download and manage research benchmarks.", no_args_is_help=True)
console = Console()


@benchmark_app.command("list")
def list_benchmarks() -> None:
    """List research benchmarks and their local download status."""
    table = Table(box=None)
    table.add_column("Benchmark")
    table.add_column("Status")
    for name in dataset_registry.list_names():
        benchmark = dataset_registry.get_class(name).installation
        status = "downloaded" if benchmark.is_downloaded else "not downloaded"
        table.add_row(name, status)
    console.print(table)


@benchmark_app.command()
def download(
    name: str = typer.Argument(help="Benchmark name."),
    force: bool = typer.Option(False, "--force", help="Replace an existing invalid installation."),
) -> None:
    """Download and verify a complete benchmark."""
    try:
        benchmark = dataset_registry.get_class(name).installation
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="name") from None

    if benchmark.is_downloaded and not force:
        console.print(f"{name} is already downloaded at {benchmark.directory}")
        return
    if force and benchmark.fetch is not None and benchmark.directory.exists():
        typer.confirm(f"Replace {benchmark.directory}?", abort=True)

    try:
        path = asyncio.run(benchmark.install(force=force, progress=lambda message: console.print(f"{message}...")))
    except BenchmarkInstallationError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None
    except httpx.HTTPError as error:
        console.print(f"[red]Download failed:[/red] {error}")
        raise typer.Exit(1) from None
    console.print(f"{name} downloaded to {path}")


__all__ = ["benchmark_app"]
