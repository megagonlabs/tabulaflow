"""Process-wide resources used by TabulaFlow agents."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

from aiolimiter import AsyncLimiter

from tabulaflow.agents.config import AgentRuntimeConfig

if TYPE_CHECKING:
    from tabulaflow.agents.tools.web_browser import WebBrowserManager

_ModelT = TypeVar("_ModelT")
_ThrottlePair = tuple[asyncio.Semaphore | None, AsyncLimiter | None]


class _AgentRuntime:
    def __init__(self, config: AgentRuntimeConfig) -> None:
        self.config = config
        self._llm_throttles: dict[int, _ThrottlePair] = {}
        self._embedding_throttles: dict[int, _ThrottlePair] = {}
        self._base_models: dict[int, dict[str, Any]] = {}
        self._browser_manager: WebBrowserManager | None = None
        self._resource_lock = threading.Lock()

    def llm_throttles(self) -> _ThrottlePair:
        return self._throttles(
            self._llm_throttles,
            self.config.max_llm_concurrency,
            self.config.max_llm_requests_per_minute,
        )

    def embedding_throttles(self) -> _ThrottlePair:
        return self._throttles(
            self._embedding_throttles,
            self.config.max_embedding_concurrency,
            self.config.max_embedding_requests_per_minute,
        )

    def get_base_model(self, name: str, factory: Callable[[], _ModelT]) -> _ModelT:
        loop_id = id(asyncio.get_running_loop())
        per_loop = self._base_models.setdefault(loop_id, {})
        if name not in per_loop:
            per_loop[name] = factory()
        return cast(_ModelT, per_loop[name])

    def get_browser_manager(self) -> WebBrowserManager:
        if self._browser_manager is None:
            with self._resource_lock:
                if self._browser_manager is None:
                    from tabulaflow.agents.tools.web_browser import WebBrowserManager

                    self._browser_manager = WebBrowserManager(
                        headless=self.config.browser_headless,
                        max_pages=self.config.browser_max_tabs,
                    )
        return self._browser_manager

    async def close(self) -> None:
        if self._browser_manager is not None:
            await self._browser_manager.close()
        self._llm_throttles.clear()
        self._embedding_throttles.clear()
        self._base_models.clear()
        self._browser_manager = None

    @staticmethod
    def _throttles(
        cache: dict[int, _ThrottlePair],
        max_concurrency: int | None,
        max_requests_per_minute: int | None,
    ) -> _ThrottlePair:
        loop_id = id(asyncio.get_running_loop())
        if loop_id not in cache:
            semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency is not None else None
            limiter = AsyncLimiter(max_requests_per_minute, 60) if max_requests_per_minute is not None else None
            cache[loop_id] = (semaphore, limiter)
        return cache[loop_id]


_runtime: _AgentRuntime | None = None
_runtime_lock = threading.Lock()


def initialize_agent_runtime(config: AgentRuntimeConfig) -> None:
    """Initialize the process-wide agent runtime before its first use."""
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            raise RuntimeError("The agent runtime has already been initialized")
        _runtime = _AgentRuntime(config)


def _get_agent_runtime() -> _AgentRuntime:
    global _runtime
    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                _runtime = _AgentRuntime(AgentRuntimeConfig())
    return _runtime


async def _reset_agent_runtime_for_tests() -> None:
    global _runtime
    with _runtime_lock:
        runtime = _runtime
        _runtime = None
    if runtime is not None:
        await runtime.close()


__all__ = ["initialize_agent_runtime"]
