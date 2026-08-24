from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncIterator, ClassVar, Literal

import pytest
from pydantic import BaseModel

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.agents.modules import CachedPreprocessorMixin
from tabulaflow.agents.runtime import _get_agent_runtime, _reset_agent_runtime_for_tests


@pytest.fixture(autouse=True)
async def reset_runtime() -> AsyncIterator[None]:
    await _reset_agent_runtime_for_tests()
    yield
    await _reset_agent_runtime_for_tests()


def test_runtime_is_lazily_initialized_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_LLM_CONCURRENCY", "7")

    runtime = _get_agent_runtime()

    assert runtime.config.max_llm_concurrency == 7


def test_explicit_runtime_initialization_is_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_LLM_CONCURRENCY", "7")
    initialize_agent_runtime(AgentRuntimeConfig(max_llm_concurrency=3))

    monkeypatch.setenv("TABULAFLOW_MAX_LLM_CONCURRENCY", "9")

    assert _get_agent_runtime().config.max_llm_concurrency == 3


def test_runtime_cannot_be_initialized_twice() -> None:
    initialize_agent_runtime(AgentRuntimeConfig())

    with pytest.raises(RuntimeError, match="already been initialized"):
        initialize_agent_runtime(AgentRuntimeConfig())


def test_runtime_cannot_be_initialized_after_lazy_use() -> None:
    _get_agent_runtime()

    with pytest.raises(RuntimeError, match="already been initialized"):
        initialize_agent_runtime(AgentRuntimeConfig())


async def test_runtime_shares_loop_bound_resources() -> None:
    runtime = _get_agent_runtime()
    builds = 0

    def build() -> object:
        nonlocal builds
        builds += 1
        return object()

    assert runtime.llm_throttles() is runtime.llm_throttles()
    assert runtime.embedding_throttles() is runtime.embedding_throttles()
    assert runtime.get_base_model("model", build) is runtime.get_base_model("model", build)
    assert builds == 1


async def test_runtime_owns_the_default_browser_manager() -> None:
    from tabulaflow.agents.tools.web_browser import WebBrowserTool

    initialize_agent_runtime(AgentRuntimeConfig(browser_headless=False, browser_max_tabs=4))
    runtime = _get_agent_runtime()

    manager = runtime.get_browser_manager()

    assert manager is runtime.get_browser_manager()
    assert await WebBrowserTool()._ensure_manager() is manager
    assert manager._headless is False
    assert manager._page_budget._limit == 4


class _CachedValue(BaseModel):
    value: int


class _Preprocessor(CachedPreprocessorMixin[_CachedValue]):
    name: ClassVar = "test"
    input_type: ClassVar = "db_connector"
    output_type: ClassVar = _CachedValue

    def __init__(self) -> None:
        self.calls = 0

    async def _preprocess_impl_async(self, input_data: Any) -> _CachedValue:
        self.calls += 1
        return _CachedValue(value=self.calls)


@pytest.mark.parametrize(
    ("mode", "expected_calls", "writes_cache"),
    [
        ("off", 2, False),
        ("read_write", 1, True),
        ("refresh", 2, True),
    ],
)
async def test_preprocessor_cache_modes(
    tmp_path: Path,
    mode: Literal["off", "read_write", "refresh", "cache_only"],
    expected_calls: int,
    writes_cache: bool,
) -> None:
    initialize_agent_runtime(AgentRuntimeConfig(cache_dir=tmp_path, preprocessor_cache_mode=mode))
    preprocessor = _Preprocessor()
    input_data = SimpleNamespace(global_id="db")

    await preprocessor.preprocess_async(input_data)
    await preprocessor.preprocess_async(input_data)

    assert preprocessor.calls == expected_calls
    assert (tmp_path / "preprocessors" / "test" / "db.json").exists() is writes_cache


async def test_preprocessor_cache_only_reads_existing_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "preprocessors" / "test"
    cache_dir.mkdir(parents=True)
    (cache_dir / "db.json").write_text('{"value": 42}')
    initialize_agent_runtime(AgentRuntimeConfig(cache_dir=tmp_path, preprocessor_cache_mode="cache_only"))
    preprocessor = _Preprocessor()

    result = await preprocessor.preprocess_async(SimpleNamespace(global_id="db"))

    assert result == _CachedValue(value=42)
    assert preprocessor.calls == 0


async def test_preprocessor_cache_only_fails_on_miss(tmp_path: Path) -> None:
    initialize_agent_runtime(AgentRuntimeConfig(cache_dir=tmp_path, preprocessor_cache_mode="cache_only"))

    with pytest.raises(FileNotFoundError, match="Preprocessor cache required"):
        await _Preprocessor().preprocess_async(SimpleNamespace(global_id="db"))
