"""Atomic installation of benchmark data."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
from huggingface_hub import snapshot_download

from tabulaflow._paths import DEFAULT_HOME_DIR

ProgressCallback = Callable[[str], None]
FetchFunction = Callable[[Path, ProgressCallback], Awaitable[None]]
DEFAULT_BENCHMARK_DIR = DEFAULT_HOME_DIR / "benchmarks"


class BenchmarkInstallationError(RuntimeError):
    """Raised when benchmark data cannot be installed."""


@dataclass(frozen=True)
class BenchmarkInstallation:
    """Local installation requirements for one benchmark."""

    name: str
    required_paths: tuple[str, ...]
    fetch: FetchFunction | None = None
    setup_url: str | None = None

    @property
    def directory(self) -> Path:
        return DEFAULT_BENCHMARK_DIR / self.name

    @property
    def missing_paths(self) -> tuple[str, ...]:
        return tuple(path for path in self.required_paths if not (self.directory / path).exists())

    @property
    def is_downloaded(self) -> bool:
        return not self.missing_paths

    async def install(self, *, force: bool = False, progress: ProgressCallback | None = None) -> Path:
        """Download, verify, and atomically install the benchmark."""
        progress = progress or (lambda _: None)
        if self.is_downloaded and (not force or self.fetch is None):
            return self.directory
        if self.fetch is None:
            lines = [f"{self.name} requires manual setup."]
            if self.setup_url:
                lines.extend((f"Setup: {self.setup_url}", ""))
            lines.append(f"Missing from {self.directory}:")
            lines.extend(f"  {path}" for path in self.missing_paths)
            raise BenchmarkInstallationError("\n".join(lines))
        if self.directory.exists() and not force:
            raise BenchmarkInstallationError(
                f"{self.directory} exists but is not a valid {self.name} installation; use --force to replace it"
            )

        self.directory.parent.mkdir(parents=True, exist_ok=True)
        downloads_dir = self.directory.parent / ".downloads"
        downloads_dir.mkdir(exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f"{self.name}-", dir=downloads_dir))
        try:
            await self.fetch(staging, progress)
            missing = [path for path in self.required_paths if not (staging / path).exists()]
            if missing:
                raise BenchmarkInstallationError(f"downloaded {self.name} is missing: {', '.join(missing)}")
            _replace_directory(staging, self.directory)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return self.directory


def _replace_directory(source: Path, destination: Path) -> None:
    backup = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.old")
    if destination.exists():
        destination.rename(backup)
    try:
        source.rename(destination)
    except BaseException:
        if backup.exists():
            backup.rename(destination)
        raise
    shutil.rmtree(backup, ignore_errors=True)


async def _download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                async for chunk in response.aiter_bytes():
                    output.write(chunk)


CYPHERBENCH_DATA_REVISION = "efdfde14c04fe174b4960544c1b1001530e2a178"
CYPHERBENCH_RUNTIME_REVISION = "94605181d12d9bc837f737a37b9d46471c2f3eff"


async def _download_cypherbench(destination: Path, progress: ProgressCallback) -> None:
    progress("Downloading benchmark data")
    await asyncio.to_thread(
        snapshot_download,
        repo_id="megagonlabs/cypherbench",
        repo_type="dataset",
        revision=CYPHERBENCH_DATA_REVISION,
        local_dir=destination,
    )
    runtime_files = (".env", "docker-compose-test.yml", "docker-compose-train.yml")
    progress("Downloading database runtime")
    await asyncio.gather(
        *[
            _download_file(
                "https://raw.githubusercontent.com/megagonlabs/cypherbench/"
                f"{CYPHERBENCH_RUNTIME_REVISION}/docker/{filename}",
                destination / "docker" / filename,
            )
            for filename in runtime_files
        ]
    )
    for filename in runtime_files[1:]:
        path = destination / "docker" / filename
        path.write_text(path.read_text().replace("../benchmark/graphs/", "../graphs/"))


BENCHMARK_INSTALLATIONS: dict[str, BenchmarkInstallation] = {
    "ambrosia-s": BenchmarkInstallation(
        name="ambrosia-s",
        required_paths=(
            "ambrosia/ambrosia.csv",
            "ambrosia_test_processed.json",
            "ambrosia_few_shot_examples_processed.json",
        ),
        setup_url="https://ambrosia-benchmark.github.io/",
    ),
    "arcs": BenchmarkInstallation(name="arcs", required_paths=("tasks/tasks_unsampled.json",)),
    "beaver": BenchmarkInstallation(
        name="beaver",
        required_paths=("dev_dw.json", "dev_nw.json"),
        setup_url="https://github.com/peterbaile/beaver",
    ),
    "bird-sql": BenchmarkInstallation(
        name="bird-sql",
        required_paths=(
            "dev_20240627/dev.json",
            "dev_20240627/dev_databases",
            "dev_20251106/dev.json",
            "train/train.json",
            "train/train_databases",
            "column_meaning/dev_column_meaning.json",
            "column_meaning/train_column_meaning.json",
        ),
        setup_url="https://bird-bench.github.io/",
    ),
    "cypherbench": BenchmarkInstallation(
        name="cypherbench",
        required_paths=(
            "test.json",
            "train.json",
            *(
                f"graphs/simplekg/{graph}_simplekg.json"
                for graph in (
                    "art",
                    "biology",
                    "company",
                    "fictional_character",
                    "flight_accident",
                    "geography",
                    "movie",
                    "nba",
                    "politics",
                    "soccer",
                    "terrorist_attack",
                )
            ),
            "docker/.env",
            "docker/docker-compose-test.yml",
            "docker/docker-compose-train.yml",
        ),
        fetch=_download_cypherbench,
    ),
    "spider2-dbt": BenchmarkInstallation(
        name="spider2-dbt",
        required_paths=("examples/spider2-dbt.jsonl",),
        setup_url="https://github.com/xlang-ai/Spider2",
    ),
    "spider2-lite": BenchmarkInstallation(
        name="spider2-lite",
        required_paths=("spider2-lite.jsonl",),
        setup_url="https://github.com/xlang-ai/Spider2",
    ),
    "spider2-snow": BenchmarkInstallation(
        name="spider2-snow",
        required_paths=("spider2-snow.jsonl",),
        setup_url="https://github.com/xlang-ai/Spider2",
    ),
}


def get_benchmark_installation(name: str) -> BenchmarkInstallation:
    """Return the installation definition for a benchmark name."""
    try:
        return BENCHMARK_INSTALLATIONS[name]
    except KeyError:
        available = ", ".join(BENCHMARK_INSTALLATIONS)
        raise ValueError(f"unknown benchmark {name!r}; available: {available}") from None


def require_benchmark_downloaded(name: str) -> None:
    """Raise an actionable error when a benchmark is not installed."""
    benchmark = get_benchmark_installation(name)
    if not benchmark.is_downloaded:
        raise FileNotFoundError(f"{name} is not downloaded. Run: tabulaflow benchmark download {name}")


__all__ = [
    "BENCHMARK_INSTALLATIONS",
    "BenchmarkInstallation",
    "BenchmarkInstallationError",
    "DEFAULT_BENCHMARK_DIR",
    "get_benchmark_installation",
    "require_benchmark_downloaded",
]
