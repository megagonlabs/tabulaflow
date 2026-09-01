from pathlib import Path

import pytest

from tabulaflow.research.benchmarks import installation
from tabulaflow.research.benchmarks.installation import BenchmarkInstallation, BenchmarkInstallationError


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
    assert benchmark.is_downloaded


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
    assert not benchmark.is_downloaded


def test_manual_download_is_detected_from_required_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)
    benchmark = BenchmarkInstallation(name="example", required_paths=("tasks.json",))

    assert not benchmark.is_downloaded
    benchmark.directory.mkdir()
    (benchmark.directory / "tasks.json").write_text("[]")
    assert benchmark.is_downloaded


@pytest.mark.asyncio
async def test_manual_setup_error_is_actionable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installation, "DEFAULT_BENCHMARK_DIR", tmp_path)
    benchmark = BenchmarkInstallation(
        name="example",
        required_paths=("tasks.json", "databases"),
        setup_url="https://example.com/setup",
    )

    with pytest.raises(BenchmarkInstallationError) as error:
        await benchmark.install()

    message = str(error.value)
    assert "Setup: https://example.com/setup" in message
    assert f"Missing from {tmp_path / 'example'}:" in message
    assert "  tasks.json" in message
    assert "  databases" in message


@pytest.mark.asyncio
async def test_cypherbench_uses_a_flat_installation_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def snapshot_download(**kwargs: object) -> None:
        assert kwargs["local_dir"] == tmp_path
        (tmp_path / "test.json").write_text("[]")

    async def download_file(url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("../benchmark/graphs/simplekg/example.json")

    monkeypatch.setattr(installation, "snapshot_download", snapshot_download)
    monkeypatch.setattr(installation, "_download_file", download_file)

    await installation._download_cypherbench(tmp_path, lambda _: None)

    compose = (tmp_path / "docker" / "docker-compose-test.yml").read_text()
    assert compose == "../graphs/simplekg/example.json"
