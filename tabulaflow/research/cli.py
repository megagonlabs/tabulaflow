"""Command-line interface for research benchmarks."""

import asyncio
from typing import cast

import httpx
import typer
from rich.console import Console
from rich.table import Table

from tabulaflow.research.benchmarks.installation import BenchmarkInstallationError
from tabulaflow.research.benchmarks.registry import DatasetLoaderProtocol, dataset_registry
from tabulaflow.research.benchmarks.runtime import BenchmarkRuntime, BenchmarkRuntimeError

benchmark_app = typer.Typer(help="Download and manage research benchmarks.", no_args_is_help=True)
console = Console()


def _get_benchmark(name: str) -> type[DatasetLoaderProtocol]:
    try:
        return dataset_registry.get_class(name)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="name") from None


def _get_runtime(name: str) -> BenchmarkRuntime:
    runtime = cast(BenchmarkRuntime | None, getattr(_get_benchmark(name), "runtime", None))
    if runtime is None:
        raise typer.BadParameter(f"{name} does not have a managed database runtime", param_hint="name")
    return runtime


def _progress(message: str) -> None:
    console.print(f"{message}...")


@benchmark_app.command("list")
def list_benchmarks() -> None:
    """List research benchmarks and their local download status."""
    table = Table(box=None)
    table.add_column("Benchmark")
    table.add_column("Status")
    for name in dataset_registry.list_names():
        benchmark = dataset_registry.get_class(name).installation
        status = "downloaded" if benchmark.is_installed else "not downloaded"
        table.add_row(name, status)
    console.print(table)


@benchmark_app.command()
def download(
    name: str = typer.Argument(help="Benchmark name."),
    force: bool = typer.Option(False, "--force", help="Replace an existing invalid installation."),
) -> None:
    """Download and verify a complete benchmark."""
    benchmark = _get_benchmark(name).installation

    if benchmark.is_installed and not force:
        console.print(f"{name} is already downloaded at {benchmark.directory}")
        return
    if force and benchmark.fetch is not None and benchmark.directory.exists():
        typer.confirm(f"Replace {benchmark.directory}?", abort=True)

    console.print(f"Downloading {name} to {benchmark.directory}")
    try:
        path = asyncio.run(benchmark.install(force=force, progress=_progress))
    except BenchmarkInstallationError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None
    except httpx.HTTPError as error:
        console.print(f"[red]Download failed:[/red] {error}")
        raise typer.Exit(1) from None
    console.print(f"{name} downloaded to {path}")


@benchmark_app.command()
def start(
    name: str = typer.Argument(help="Benchmark name."),
    split: str | None = typer.Option(None, "--split", help="Database split to start."),
) -> None:
    """Download a benchmark if needed and start its managed databases."""
    benchmark = _get_benchmark(name)
    runtime = _get_runtime(name)
    if not benchmark.installation.is_installed:
        console.print(f"Downloading {name} to {benchmark.installation.directory}")

    async def start_runtime() -> None:
        await benchmark.installation.install(progress=_progress)
        await runtime.start(split, _progress)

    try:
        asyncio.run(start_runtime())
    except (BenchmarkInstallationError, BenchmarkRuntimeError, httpx.HTTPError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None
    console.print(f"{name} databases started")


@benchmark_app.command()
def stop(
    name: str = typer.Argument(help="Benchmark name."),
    split: str | None = typer.Option(None, "--split", help="Database split to stop."),
) -> None:
    """Stop a benchmark's managed databases without deleting their data."""
    benchmark = _get_benchmark(name)
    runtime = _get_runtime(name)
    try:
        benchmark.installation.require()
        asyncio.run(runtime.stop(split, _progress))
    except (FileNotFoundError, BenchmarkRuntimeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None
    console.print(f"{name} databases stopped")


__all__ = ["benchmark_app"]
