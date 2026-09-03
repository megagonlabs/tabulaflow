import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncIterator, Literal, cast

import pytest
from pydantic import BaseModel
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.models.test import TestModel

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.agents._cache import InvalidCacheEntry, load_or_compute_model
from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.summarization import DBSummarizer
from tabulaflow.core._cache import write_cached_model
from tabulaflow.core.schema import SQLSchema
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


async def test_agents_default_to_unlimited_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_limits: list[UsageLimits] = []

    async def run(_self: Agent[Any, Any], *_args: Any, **kwargs: Any) -> None:
        captured_limits.append(kwargs["usage_limits"])

    monkeypatch.setattr(Agent, "run", run)
    agent = make_agent(TestModel())

    await agent.run("test", usage_limits=None)
    finite_limit = UsageLimits(request_limit=3)
    await agent.run("test", usage_limits=finite_limit)

    assert captured_limits[0].request_limit is None
    assert captured_limits[1] is finite_limit


def test_agents_default_to_three_retries() -> None:
    agent = make_agent(TestModel())

    assert agent._max_tool_retries == 3
    assert agent._max_output_retries == 3


def test_runtime_separates_resources_between_event_loops() -> None:
    runtime = _get_agent_runtime()

    async def resources() -> tuple[object, object]:
        return runtime.llm_throttles(), runtime.get_base_model("model", object)

    first = asyncio.run(resources())
    second = asyncio.run(resources())

    assert first[0] is not second[0]
    assert first[1] is not second[1]


async def test_runtime_owns_the_default_browser_manager() -> None:
    from tabulaflow.agents.tools.browser.tool import WebBrowserTool

    initialize_agent_runtime(AgentRuntimeConfig(browser_headless=False, browser_max_tabs=4))
    runtime = _get_agent_runtime()

    manager = runtime.get_browser_manager()

    assert manager is runtime.get_browser_manager()
    assert await WebBrowserTool()._ensure_manager() is manager
    assert manager._headless is False
    assert manager._page_budget._limit == 4


class _CachedValue(BaseModel):
    value: int


@pytest.mark.parametrize(
    ("mode", "expected_calls", "writes_cache"),
    [
        ("off", 2, False),
        ("read_write", 1, True),
        ("refresh", 2, True),
    ],
)
async def test_agent_cache_modes(
    tmp_path: Path,
    mode: Literal["off", "read_write", "refresh", "cache_only"],
    expected_calls: int,
    writes_cache: bool,
) -> None:
    path = tmp_path / "value.json"
    calls = 0

    async def compute() -> _CachedValue:
        nonlocal calls
        calls += 1
        return _CachedValue(value=calls)

    await load_or_compute_model(path=path, mode=mode, model_type=_CachedValue, compute=compute)
    await load_or_compute_model(path=path, mode=mode, model_type=_CachedValue, compute=compute)

    assert calls == expected_calls
    assert path.exists() is writes_cache


async def test_agent_cache_only_reads_existing_cache(tmp_path: Path) -> None:
    path = tmp_path / "value.json"
    await write_cached_model(path, _CachedValue(value=42))

    async def compute() -> _CachedValue:
        raise AssertionError("cache-only mode must not compute")

    result = await load_or_compute_model(
        path=path,
        mode="cache_only",
        model_type=_CachedValue,
        compute=compute,
    )

    assert result == _CachedValue(value=42)


async def test_agent_cache_only_fails_on_miss(tmp_path: Path) -> None:
    async def compute() -> _CachedValue:
        raise AssertionError("cache-only mode must not compute")

    with pytest.raises(FileNotFoundError, match="Cache entry not found"):
        await load_or_compute_model(
            path=tmp_path / "missing.json",
            mode="cache_only",
            model_type=_CachedValue,
            compute=compute,
        )


async def test_agent_cache_recomputes_invalid_entry_unless_cache_only(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("not json")

    async def compute() -> _CachedValue:
        return _CachedValue(value=7)

    result = await load_or_compute_model(
        path=path,
        mode="read_write",
        model_type=_CachedValue,
        compute=compute,
    )
    assert result == _CachedValue(value=7)

    path.write_text("not json")
    with pytest.raises(InvalidCacheEntry):
        await load_or_compute_model(
            path=path,
            mode="cache_only",
            model_type=_CachedValue,
            compute=compute,
        )


async def test_database_summarizer_owns_versioned_semantic_cache_key(tmp_path: Path) -> None:
    initialize_agent_runtime(AgentRuntimeConfig(cache_dir=tmp_path, preprocessing_cache_mode="read_write"))
    connector = cast(
        Any,
        SimpleNamespace(
            connector_type="sql",
            global_id="empty-db",
            schema=SQLSchema(name="empty", dialect="sqlite", tables=[]),
        ),
    )
    summarizer = DBSummarizer(max_words=100)

    summary = await summarizer.summarize(connector)
    cached = await summarizer.summarize(connector)

    assert summary == cached
    assert len(list((tmp_path / "agent" / "db_summaries").glob("v2@*.md"))) == 1
    changed = DBSummarizer(max_words=200)
    await changed.summarize(connector)
    assert len(list((tmp_path / "agent" / "db_summaries").glob("v2@*.md"))) == 2
