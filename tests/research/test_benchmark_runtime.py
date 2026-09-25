from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable

from tabulaflow.research.benchmarks import beaver, cypherbench
from tabulaflow.research.benchmarks import registry
from tabulaflow.research.benchmarks.runtime import BenchmarkRuntime, BenchmarkRuntimeError


async def _noop(split: str | None, progress: Callable[[str], None]) -> None:
    return None


async def _ready(split: str | None) -> bool:
    return True


def test_runtime_resolves_default_and_validates_splits() -> None:
    runtime = BenchmarkRuntime(
        start_action=_noop,
        stop_action=_noop,
        ready_action=_ready,
        splits=("test", "train"),
        default_split="test",
    )

    assert runtime.resolve_split(None) == "test"
    assert runtime.resolve_split("train") == "train"
    with pytest.raises(BenchmarkRuntimeError, match="unsupported split"):
        runtime.resolve_split("dev")


@pytest.mark.asyncio
async def test_runtime_preflight_reports_start_command() -> None:
    async def not_ready(split: str | None) -> bool:
        return False

    runtime = BenchmarkRuntime(
        start_action=_noop,
        stop_action=_noop,
        ready_action=not_ready,
        splits=("test", "train"),
        default_split="test",
    )

    with pytest.raises(BenchmarkRuntimeError, match="tabulaflow benchmark start example --split train"):
        await runtime.require_ready("example", "train")


@pytest.mark.asyncio
async def test_benchmark_preflight_checks_managed_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    checked: list[tuple[str, str | None]] = []

    async def ready(split: str | None) -> bool:
        checked.append(("ready", split))
        return True

    benchmark_runtime = BenchmarkRuntime(start_action=_noop, stop_action=_noop, ready_action=ready)

    class Installation:
        def require(self) -> None:
            checked.append(("installation", None))

    class Benchmark:
        installation = Installation()
        runtime = benchmark_runtime

    monkeypatch.setattr(registry.dataset_registry, "get_class", lambda name: Benchmark)

    await registry.preflight_benchmark("example", "test")

    assert checked == [("installation", None), ("ready", None)]


@pytest.mark.asyncio
async def test_cypherbench_runtime_runs_a_container_per_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    async def ensure_docker() -> None:
        return None

    async def container_exists(name: str) -> bool:
        return False

    async def run_command(*command: str, cwd: Path | None = None) -> str:
        commands.append(command)
        return ""

    async def wait_until_ready(check: Callable[[], Awaitable[bool]], description: str, **kwargs: object) -> None:
        assert await check()

    async def ready(split: str | None) -> bool:
        return split == "train"

    monkeypatch.setattr(cypherbench, "ensure_docker", ensure_docker)
    monkeypatch.setattr(cypherbench, "container_exists", container_exists)
    monkeypatch.setattr(cypherbench, "run_command", run_command)
    monkeypatch.setattr(cypherbench, "wait_until_ready", wait_until_ready)
    monkeypatch.setattr(cypherbench, "_cypherbench_ready", ready)

    await cypherbench.CYPHERBENCH_RUNTIME.start("train", lambda _: None)

    run_commands = [command for command in commands if command[:2] == ("docker", "run")]
    assert len(run_commands) == len(cypherbench.CYPHERBENCH_SPLIT_GRAPHS["train"])
    assert all(command[-1] == cypherbench.CYPHERBENCH_NEO4J_IMAGE for command in run_commands)
    art = next(command for command in run_commands if "cypherbench-art" in command)
    assert "15060:7687" in art
    assert any(item.endswith("graphs/simplekg/art_simplekg.json:/init/graph.json:ro") for item in art)


def _stub_runtime(
    monkeypatch: pytest.MonkeyPatch,
    commands: list[tuple[str, ...]],
    *,
    exists: bool,
    ready: bool,
) -> None:
    async def ensure_docker() -> None:
        return None

    async def container_exists(name: str) -> bool:
        return exists

    async def graph_ready(graph: str) -> bool:
        return ready

    async def run_command(*command: str, cwd: Path | None = None) -> str:
        commands.append(command)
        return ""

    async def wait_until_ready(check: Callable[[], Awaitable[bool]], description: str, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(cypherbench, "ensure_docker", ensure_docker)
    monkeypatch.setattr(cypherbench, "container_exists", container_exists)
    monkeypatch.setattr(cypherbench, "_graph_ready", graph_ready)
    monkeypatch.setattr(cypherbench, "run_command", run_command)
    monkeypatch.setattr(cypherbench, "wait_until_ready", wait_until_ready)


@pytest.mark.asyncio
async def test_cypherbench_start_recreates_unusable_containers(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []
    _stub_runtime(monkeypatch, commands, exists=True, ready=False)

    await cypherbench.CYPHERBENCH_RUNTIME.start("train", lambda _: None)

    removed = [command for command in commands if command[:2] == ("docker", "rm")]
    created = [command for command in commands if command[:2] == ("docker", "run")]
    assert len(removed) == len(created) == len(cypherbench.CYPHERBENCH_SPLIT_GRAPHS["train"])
    assert all("-fv" in command for command in removed)


@pytest.mark.asyncio
async def test_cypherbench_start_keeps_ready_containers(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []
    _stub_runtime(monkeypatch, commands, exists=True, ready=True)

    await cypherbench.CYPHERBENCH_RUNTIME.start("train", lambda _: None)

    assert commands == []


@pytest.mark.asyncio
async def test_cypherbench_stop_removes_containers(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []
    _stub_runtime(monkeypatch, commands, exists=True, ready=True)

    await cypherbench.CYPHERBENCH_RUNTIME.stop("train", lambda _: None)

    assert commands == [
        ("docker", "rm", "-fv", "cypherbench-art", "cypherbench-biology", "cypherbench-soccer", "cypherbench-terrorist-attack")
    ]


@pytest.mark.asyncio
async def test_graph_ready_requires_imported_data_and_live_bolt(monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []
    log_tail = "neo4j boot log\nLoaded 1683 entities and 2212 relations\n"

    class FakeDriver:
        fails: bool = True

        async def verify_connectivity(self) -> None:
            if self.fails:
                raise ServiceUnavailable("couldn't connect")

        async def close(self) -> None:
            return None

    def driver(url: str, **kwargs: object) -> FakeDriver:
        urls.append(url)
        return FakeDriver()

    async def run_command(*command: str, cwd: Path | None = None) -> str:
        return log_tail

    monkeypatch.setattr(cypherbench, "run_command", run_command)
    monkeypatch.setattr(AsyncGraphDatabase, "driver", driver)

    # Import finished but Bolt is down.
    assert await cypherbench._graph_ready("art") is False
    assert urls == [f"bolt://localhost:{cypherbench.CYPHERBENCH_DEFAULT_GRAPH_PORTS['art']}"]

    FakeDriver.fails = False
    assert await cypherbench._graph_ready("art") is True

    # Import unfinished: Bolt is never consulted.
    log_tail = "neo4j boot log\n"
    assert await cypherbench._graph_ready("art") is False
    assert len(urls) == 2

    # Container does not exist.
    async def failing_run_command(*command: str, cwd: Path | None = None) -> str:
        raise BenchmarkRuntimeError("No such container")

    monkeypatch.setattr(cypherbench, "run_command", failing_run_command)
    assert await cypherbench._graph_ready("art") is False


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
    assert all(command[:2] != ("docker", "compose") for command in commands)
    assert any("tabulaflow-beaver-dw:/var/lib/mysql" in command for command in run_commands)
    assert any("tabulaflow-beaver-nw:/var/lib/mysql" in command for command in run_commands)
