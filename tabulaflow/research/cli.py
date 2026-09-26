"""Command-line interface for research benchmarks."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import cast

import httpx
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from tabulaflow.research.benchmarks.installation import BenchmarkInstallationError
from tabulaflow.research.benchmarks.registry import DatasetLoaderProtocol, dataset_registry, preflight_benchmark
from tabulaflow.research.benchmarks.runtime import BenchmarkRuntime, BenchmarkRuntimeError

benchmark_app = typer.Typer(help="Download, run, and manage research benchmarks.", no_args_is_help=True)
console = Console(highlighter=None)

_DEFAULT_AGENTS = {
    "ambrosia-s": "ambig_structured_sql_agent",
    "arcs": "ambig_structured_sql_agent",
    "spider2-dbt": "dbt_agent",
}
_DEFAULT_AGENT = "full_schema"


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


async def _run_benchmark_async(
    name: str,
    split: str,
    sample_size: int,
    batch_size: int,
    agent_name: str,
    llm: str | None,
    output_dir: Path | None,
) -> Path:
    from tabulaflow.research.agents import agent_registry
    from tabulaflow.research.metrics import metric_registry
    from tabulaflow.research.pipelines import run_experiment_async

    benchmark = _get_benchmark(name)
    await preflight_benchmark(name, split)
    loader = benchmark()
    dataset = await loader.get_split_async(split, subsample_size=sample_size)
    try:
        agent_cls = agent_registry.get_class(agent_name)
        config_kwargs = {"llm": llm} if llm is not None else {}
        agent_config = agent_cls.config_cls(**config_kwargs)
        metric_cls = metric_registry.get_class(benchmark.default_metrics[0])
        metric = metric_cls()
        destination = output_dir or Path("runs") / name / datetime.now().strftime("%Y%m%d-%H%M%S")
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            raise ValueError(f"output path already exists and is not an empty directory: {destination}")

        console.print(f"Benchmark: {name} / {split}")
        console.print(f"Tasks: {len(dataset.tasks)}")
        console.print(f"Agent: {agent_name}")
        console.print(f"Model: {getattr(agent_config, 'llm', 'N/A')}")
        console.print(f"Metric: {metric.name}")
        console.print()

        result = await run_experiment_async(
            agent_cls,
            agent_config,
            dataset,
            [metric],
            batch_size=batch_size,
            working_dir=destination / "work",
        )
        result.to_directory(str(destination))

        score = result.aggregated_eval_metrics.get(metric.name, {}).get("avg")
        console.print()
        console.print(f"[green]Evaluated:[/green] {len(result.tasks)} tasks")
        console.print(f"{metric.name}: {score if score is not None else 'N/A'}")
        console.print(f"Results: {destination}")
        return destination
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


@benchmark_app.command("list")
def list_benchmarks() -> None:
    """List research benchmarks and their local download status."""
    table = Table(box=None)
    table.add_column("Benchmark")
    table.add_column("Status")
    for name in dataset_registry.list_names():
        benchmark = dataset_registry.get_class(name).installation
        status = Text("installed", style="green") if benchmark.is_installed else Text("not installed", style="dim")
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
        console.print("[green]Installed:[/green]", name)
        console.print("Location:", benchmark.directory)
        return
    if force and benchmark.fetch is not None and benchmark.directory.exists():
        typer.confirm(f"Replace {benchmark.directory}?", abort=True)

    console.print("Downloading", name, "to", benchmark.directory)
    try:
        path = asyncio.run(benchmark.install(force=force, progress=_progress))
    except BenchmarkInstallationError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None
    except httpx.HTTPError as error:
        console.print(f"[red]Download failed:[/red] {error}")
        raise typer.Exit(1) from None
    console.print("[green]Installed:[/green]", name)
    console.print("Location:", path)


@benchmark_app.command()
def start(
    name: str = typer.Argument(help="Benchmark name."),
    split: str | None = typer.Option(None, "--split", help="Database split to start."),
) -> None:
    """Download a benchmark if needed and start its managed databases."""
    benchmark = _get_benchmark(name)
    runtime = _get_runtime(name)
    if not benchmark.installation.is_installed:
        console.print("Downloading", name, "to", benchmark.installation.directory)

    async def start_runtime() -> None:
        await benchmark.installation.install(progress=_progress)
        await runtime.start(split, _progress)

    try:
        asyncio.run(start_runtime())
    except (BenchmarkInstallationError, BenchmarkRuntimeError, httpx.HTTPError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None
    resolved_split = runtime.resolve_split(split)
    target = f"{name} {resolved_split}" if resolved_split else name
    console.print("[green]Started:[/green]", f"{target} databases")


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
    except (BenchmarkInstallationError, BenchmarkRuntimeError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None
    resolved_split = runtime.resolve_split(split)
    target = f"{name} {resolved_split}" if resolved_split else name
    console.print("[green]Stopped:[/green]", f"{target} databases")


@benchmark_app.command("run")
def run_benchmark(
    name: str = typer.Argument(help="Benchmark name."),
    split: str | None = typer.Option(None, "--split", help="Dataset split. Defaults to the benchmark's first split."),
    sample_size: int = typer.Option(5, "--sample-size", min=1, help="Number of tasks sampled deterministically."),
    batch_size: int = typer.Option(5, "--batch-size", min=1, help="Maximum tasks processed concurrently."),
    agent: str | None = typer.Option(None, "--agent", help="Registered agent override."),
    llm: str | None = typer.Option(None, "--llm", help="Model override for the selected agent."),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Result directory."),
) -> None:
    """Run a small end-to-end benchmark experiment."""
    benchmark = _get_benchmark(name)
    resolved_split = split or benchmark.splits[0]
    if resolved_split not in benchmark.splits:
        choices = ", ".join(benchmark.splits)
        raise typer.BadParameter(f"unknown split {resolved_split!r}; choose from: {choices}", param_hint="split")
    agent_name = agent or _DEFAULT_AGENTS.get(name, _DEFAULT_AGENT)
    from tabulaflow.research.agents import agent_registry

    try:
        agent_registry.get_class(agent_name)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="agent") from None
    try:
        asyncio.run(
            _run_benchmark_async(
                name,
                resolved_split,
                sample_size,
                batch_size,
                agent_name,
                llm,
                output_dir,
            )
        )
    except (BenchmarkInstallationError, BenchmarkRuntimeError, ValueError) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from None


__all__ = ["benchmark_app"]
