from pathlib import Path
import zipfile
from collections.abc import Callable
from io import BytesIO

import httpx
import pandas as pd
import pytest

from tabulaflow.research.benchmarks import installation
from tabulaflow.research.benchmarks import ambrosia_s, beaver, bird_sql, spider2_dbt
from tabulaflow.research.benchmarks import cypherbench
from tabulaflow.research.benchmarks.installation import (
    BenchmarkInstallation,
    BenchmarkInstallationError,
    extract_zip,
)
from tabulaflow.research.benchmarks.registry import dataset_registry


@pytest.mark.asyncio
async def test_download_is_atomic_and_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)
    calls = 0

    async def fetch(destination: Path, progress: installation.ProgressCallback) -> None:
        nonlocal calls
        calls += 1
        progress("fetching")
        (destination / "data").mkdir()
        (destination / "data" / "tasks.json").write_text("[]")

    benchmark = BenchmarkInstallation(
        name="example",
        required_paths=("data/tasks.json",),
        fetch=fetch,
    )
    messages: list[str] = []

    await benchmark.install(progress=messages.append)
    await benchmark.install(progress=messages.append)

    assert calls == 1
    assert messages == ["fetching"]
    assert benchmark.is_installed


@pytest.mark.asyncio
async def test_download_does_not_install_invalid_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)

    async def fetch(destination: Path, progress: installation.ProgressCallback) -> None:
        (destination / "other.txt").write_text("wrong")

    benchmark = BenchmarkInstallation(
        name="example",
        required_paths=("tasks.json",),
        fetch=fetch,
    )

    with pytest.raises(BenchmarkInstallationError, match="missing: tasks.json"):
        await benchmark.install()

    assert not benchmark.directory.exists()
    assert not benchmark.is_installed


@pytest.mark.asyncio
async def test_failed_installation_resumes_from_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)
    attempts = 0

    async def fetch(destination: Path, progress: installation.ProgressCallback) -> None:
        nonlocal attempts
        attempts += 1
        partial = destination / "partial"
        if attempts == 1:
            partial.write_text("downloaded")
            raise RuntimeError("interrupted")
        assert partial.read_text() == "downloaded"
        (destination / "tasks.json").write_text("[]")

    benchmark = BenchmarkInstallation(name="example", required_paths=("tasks.json",), fetch=fetch)

    with pytest.raises(RuntimeError, match="interrupted"):
        await benchmark.install()
    await benchmark.install()

    assert benchmark.is_installed


def test_manual_download_is_detected_from_required_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)
    benchmark = BenchmarkInstallation(name="example", required_paths=("tasks.json",))

    assert not benchmark.is_installed
    benchmark.directory.mkdir()
    (benchmark.directory / "tasks.json").write_text("[]")
    assert benchmark.is_installed


def test_missing_benchmark_error_is_actionable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)
    benchmark = BenchmarkInstallation(name="example", required_paths=("tasks.json",))

    with pytest.raises(
        BenchmarkInstallationError,
        match=r"example is not downloaded\.\s+Run:\s+tabulaflow benchmark download example",
    ):
        benchmark.require()


@pytest.mark.asyncio
async def test_manual_setup_error_shows_destination_and_missing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)
    benchmark = BenchmarkInstallation(
        name="example",
        required_paths=("tasks.json", "databases"),
    )

    with pytest.raises(BenchmarkInstallationError) as error:
        await benchmark.install()

    message = str(error.value)
    assert f"Missing from {tmp_path / 'example'}:" in message
    assert "  tasks.json" in message
    assert "  databases" in message


@pytest.mark.asyncio
async def test_cypherbench_uses_a_flat_installation_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def snapshot_download(**kwargs: object) -> None:
        assert kwargs["local_dir"] == tmp_path
        assert kwargs["revision"] == cypherbench.CYPHERBENCH_DATA_REVISION
        (tmp_path / "test.json").write_text("[]")

    monkeypatch.setattr(cypherbench, "snapshot_download", snapshot_download)

    await cypherbench._fetch_cypherbench(tmp_path, lambda _: None)

    assert (tmp_path / "test.json").exists()


def test_every_public_benchmark_has_an_automatic_installer() -> None:
    manual = {"arcs"}

    for name in dataset_registry.list_names():
        benchmark = dataset_registry.get_class(name).installation
        assert (benchmark.fetch is None) == (name in manual)
        assert benchmark.directory.name == name


def test_zip_extraction_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("../outside.txt", "unsafe")

    with pytest.raises(BenchmarkInstallationError, match="unsafe path"):
        extract_zip(archive, tmp_path / "output")


def test_download_size_uses_response_headers() -> None:
    complete = httpx.Response(200, headers={"Content-Length": "100"})
    resumed = httpx.Response(206, headers={"Content-Range": "bytes 40-99/100", "Content-Length": "60"})

    assert installation._download_size(complete, 0) == 100
    assert installation._download_size(resumed, 40) == 100


@pytest.mark.asyncio
async def test_download_zip_rejects_non_zip_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def download_file(url: str, destination: Path, **kwargs: object) -> None:
        destination.write_text("html")

    monkeypatch.setattr(installation, "download_file", download_file)
    destination = tmp_path / "archive.zip"

    with pytest.raises(BenchmarkInstallationError, match="not a ZIP"):
        await installation.download_zip("url", destination)

    assert not destination.exists()


@pytest.mark.asyncio
async def test_bird_archive_is_normalized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.zip"
    databases = BytesIO()
    with zipfile.ZipFile(databases, "w") as zip_file:
        zip_file.writestr("dev_databases/db/db.sqlite", "db")
    with zipfile.ZipFile(source, "w") as zip_file:
        zip_file.writestr("upstream/dev/dev.json", "[]")
        zip_file.writestr("upstream/dev/dev_databases.zip", databases.getvalue())

    async def download_zip(url: str, destination: Path) -> None:
        destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(bird_sql, "download_zip", download_zip)
    destination = tmp_path / "install"
    destination.mkdir()

    await bird_sql._fetch_bird_archive(destination, "dev_20240627", "url", "dev.json", "dev_databases")

    assert (destination / "dev_20240627/dev.json").is_file()
    assert (destination / "dev_20240627/dev_databases/db/db.sqlite").is_file()


def test_ambrosia_annotations_are_prepared(tmp_path: Path) -> None:
    data_dir = tmp_path / "ambrosia"
    data_dir.mkdir()
    pd.DataFrame([{"question": "Question", "gold_queries": "SELECT 1"}]).to_csv(data_dir / "ambrosia.csv", index=False)
    (tmp_path / "ambrosia_test.json").write_text('[{"qid": "0", "gold_exec_results": [[{"value": 1}]]}]')

    ambrosia_s._prepare_ambrosia_annotations(tmp_path, "test")

    output = (tmp_path / "ambrosia_test_processed.json").read_text()
    assert '"question": "Question"' in output
    assert '"query": "SELECT 1"' in output


@pytest.mark.parametrize(
    ("installer", "target"),
    [
        (beaver._install_beaver_database, "db.sql"),
        (spider2_dbt._install_dbt_databases, "database/db.duckdb"),
    ],
)
def test_database_archives_are_normalized(
    tmp_path: Path,
    installer: Callable[[Path, Path], None],
    target: str,
) -> None:
    archive = tmp_path / "database.zip"
    filename = "database/db.duckdb" if target.endswith("duckdb") else "nested/db.sql"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr(filename, "database")
    destination = tmp_path / "installed"

    installer(archive, destination)

    assert (destination / target).is_file()
