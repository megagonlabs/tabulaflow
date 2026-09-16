"""Tests for data connector registry lifecycle behavior."""

import asyncio
from typing import cast

import pytest

from tabulaflow.data.protocols import DataConnector
from tabulaflow.data.registry import DataConnectorRegistry


class CloseRecorder:
    language = "sqlite"
    schema = None
    backend = "sqlite"
    read_only = True

    def __init__(self, global_id: str, *, error: Exception | None = None) -> None:
        self.global_id = global_id
        self.error = error
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()
        self.closed = False

    async def close_async(self) -> None:
        self.started.set()
        await self.release.wait()
        self.closed = True
        if self.error is not None:
            raise self.error


def _register(registry: DataConnectorRegistry, alias: str, connector: CloseRecorder) -> None:
    registry.register(alias, cast(DataConnector, connector))


async def test_close_all_removes_aliases_and_attempts_every_close() -> None:
    registry = DataConnectorRegistry()
    failed = CloseRecorder("failed", error=ValueError("first close failed"))
    also_failed = CloseRecorder("also_failed", error=OSError("second close failed"))
    succeeded = CloseRecorder("succeeded")
    _register(registry, "failed", failed)
    _register(registry, "also_failed", also_failed)
    _register(registry, "succeeded", succeeded)

    with pytest.raises(ExceptionGroup) as exc_info:
        await registry.close_all_async()

    assert registry.list_aliases() == []
    assert failed.closed
    assert also_failed.closed
    assert succeeded.closed
    assert [str(error) for error in exc_info.value.exceptions] == ["first close failed", "second close failed"]
    assert isinstance(exc_info.value.exceptions[0], ValueError)
    assert isinstance(exc_info.value.exceptions[1], OSError)
    assert exc_info.value.exceptions[0].__notes__ == ["Connector alias: failed"]
    assert exc_info.value.exceptions[1].__notes__ == ["Connector alias: also_failed"]

    await registry.close_all_async()
    replacement = CloseRecorder("replacement")
    _register(registry, "failed", replacement)
    assert await registry.close_async("failed")
    assert replacement.closed


async def test_context_closes_owned_connectors_on_error() -> None:
    connector = CloseRecorder("connector")

    with pytest.raises(RuntimeError, match="failed inside context"):
        async with DataConnectorRegistry() as registry:
            _register(registry, "connector", connector)
            raise RuntimeError("failed inside context")

    assert connector.closed


async def test_close_all_finishes_cleanup_before_propagating_cancellation() -> None:
    registry = DataConnectorRegistry()
    first = CloseRecorder("first")
    first.release.clear()
    second = CloseRecorder("second")
    _register(registry, "first", first)
    _register(registry, "second", second)

    task = asyncio.create_task(registry.close_all_async())
    await first.started.wait()
    assert registry.list_aliases() == []

    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    first.release.set()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert first.closed
    assert second.closed


async def test_close_one_propagates_cancellation() -> None:
    registry = DataConnectorRegistry()
    connector = CloseRecorder("connector")
    connector.release.clear()
    _register(registry, "connector", connector)

    task = asyncio.create_task(registry.close_async("connector"))
    await connector.started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert not registry.has("connector")
    assert not connector.closed
