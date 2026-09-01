from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from tabulaflow.research.benchmarks import beaver, cypherbench
from tabulaflow.research.benchmarks.runtime import BenchmarkRuntime, BenchmarkRuntimeError


async def _noop(split: str | None, progress: Callable[[str], None]) -> None:
    return None


def test_runtime_resolves_default_and_validates_splits() -> None:
    runtime = BenchmarkRuntime(
        start_action=_noop,
        stop_action=_noop,
        splits=("test", "train"),
        default_split="test",
    )

    assert runtime.resolve_split(None) == "test"
    assert runtime.resolve_split("train") == "train"
    with pytest.raises(BenchmarkRuntimeError, match="unsupported split"):
        runtime.resolve_split("dev")


@pytest.mark.asyncio
async def test_cypherbench_runtime_uses_split_compose_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[tuple[str, ...], Path | None]] = []

    async def ensure_docker() -> None:
        return None

    async def run_command(*command: str, cwd: Path | None = None) -> str:
        commands.append((command, cwd))
        return ""

    async def wait_until_ready(check: Callable[[], Awaitable[bool]], description: str, **kwargs: object) -> None:
        assert await check()

    async def ready(split: str) -> bool:
        return split == "train"

    monkeypatch.setattr(cypherbench, "ensure_docker", ensure_docker)
    monkeypatch.setattr(cypherbench, "run_command", run_command)
    monkeypatch.setattr(cypherbench, "wait_until_ready", wait_until_ready)
    monkeypatch.setattr(cypherbench, "_cypherbench_ready", ready)

    await cypherbench.CYPHERBENCH_RUNTIME.start("train", lambda _: None)

    command, cwd = commands[0]
    assert "docker-compose-train.yml" in command
    assert cwd == cypherbench.CYPHERBENCH_INSTALLATION.directory / "docker"


@pytest.mark.asyncio
async def test_beaver_runtime_creates_persistent_mysql_containers(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    async def ensure_docker() -> None:
        return None

    async def container_exists(name: str) -> bool:
        return False

    async def run_command(*command: str, cwd: Path | None = None) -> str:
        commands.append(command)
        return ""

    async def wait_until_ready(check: Callable[[], Awaitable[bool]], description: str, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(beaver, "ensure_docker", ensure_docker)
    monkeypatch.setattr(beaver, "container_exists", container_exists)
    monkeypatch.setattr(beaver, "run_command", run_command)
    monkeypatch.setattr(beaver, "wait_until_ready", wait_until_ready)

    await beaver.BEAVER_RUNTIME.start(None, lambda _: None)

    run_commands = [command for command in commands if command[:2] == ("docker", "run")]
    assert len(run_commands) == 2
    assert any("tabulaflow-beaver-dw:/var/lib/mysql" in command for command in run_commands)
    assert any("tabulaflow-beaver-nw:/var/lib/mysql" in command for command in run_commands)
