"""LLM model factory.

Every pydantic-ai ``Agent`` in tabulaflow takes its model from :func:`make_model`,
so concurrency/RPM throttling, ``<tool_call>`` parsing, and Claude-on-Vertex
resolution apply *by construction*. This replaces the global monkey-patches that
used to live in ``patches.py`` (which hijacked ``pydantic_ai.models.infer_model``
and ``Model.request`` process-wide). Importing this module has no side effects.

Run agents with ``usage_limits=DEFAULT_USAGE_LIMITS`` to lift pydantic-ai's
default 50-request cap (multi-step tool loops need it).
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncIterator, TypeVar, cast, overload

from aiolimiter import AsyncLimiter
from pydantic_ai import Agent, ToolOutput, UsageLimits
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models import Model, ModelRequestParameters, infer_model
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.profiles.anthropic import (
    ANTHROPIC_THINKING_BUDGET_MAP,
    AnthropicModelProfile,
    anthropic_model_profile,
)
from pydantic_ai.settings import ModelSettings

from tabulaflow.core.config import tabulaflow_config

# Multi-step agents must not hit pydantic-ai's default 50-request cap. Pass this
# to ``agent.run(..., usage_limits=DEFAULT_USAGE_LIMITS)``.
DEFAULT_USAGE_LIMITS = UsageLimits(request_limit=None)

_ANTHROPIC_ANSWER_TOKEN_HEADROOM = 8192


def make_model_settings(
    *,
    model: str,
    reasoning_effort: str | bool | None = None,
    service_tier: str | None = None,
    timeout: float | None = None,
) -> ModelSettings:
    """Build pydantic-ai model settings from provider-neutral LLM config.

    Args:
        model: Provider-qualified model identifier (e.g. ``anthropic:claude-...``).
        reasoning_effort: Unified thinking level, translated per provider.
        service_tier: Provider service tier, for providers that expose one.
        timeout: Per-request timeout in seconds. On timeout the provider SDK
            retries the request automatically, so this doubles as a hang
            watchdog for non-streaming calls.
    """
    return cast(
        ModelSettings,
        {
            **_reasoning_model_settings(reasoning_effort, model=model),
            **_anthropic_token_settings(reasoning_effort, model=model),
            **_service_tier_model_settings(service_tier, model=model),
            **({} if timeout is None else {"timeout": timeout}),
        },
    )


def _reasoning_model_settings(reasoning_effort: str | bool | None, *, model: str) -> ModelSettings:
    """Return provider-specific reasoning settings.

    ``pydantic-ai`` uses ``thinking`` as the provider-neutral reasoning knob.
    The legacy OpenAI-specific value ``"none"`` maps to ``False``. OpenAI
    Responses models get detailed reasoning summaries whenever thinking is
    enabled.
    """
    if reasoning_effort is None:
        return ModelSettings()
    thinking: object = False if reasoning_effort == "none" else reasoning_effort
    settings = ModelSettings(thinking=cast(Any, thinking))
    if thinking is not False and model.startswith("openai-responses:"):
        settings = cast(ModelSettings, {**settings, "openai_reasoning_summary": "detailed"})
    return settings


def _anthropic_token_settings(reasoning_effort: str | bool | None, *, model: str) -> ModelSettings:
    """Give budget-thinking Claude models enough output tokens for thinking and an answer."""
    if reasoning_effort is None or reasoning_effort is False or reasoning_effort == "none":
        return ModelSettings()
    if model.startswith("anthropic:") or model.startswith("google-vertex:claude"):
        model_name = model.split(":", 1)[1]
    else:
        return ModelSettings()

    profile = AnthropicModelProfile.from_profile(anthropic_model_profile(model_name))
    if profile.anthropic_supports_adaptive_thinking:
        return ModelSettings()
    budget = ANTHROPIC_THINKING_BUDGET_MAP.get(cast(Any, reasoning_effort))
    if budget is None:
        return ModelSettings()
    return ModelSettings(max_tokens=budget + _ANTHROPIC_ANSWER_TOKEN_HEADROOM)


def _service_tier_model_settings(service_tier: str | None, *, model: str) -> ModelSettings:
    """Return provider-specific model settings for a provider-neutral service tier."""
    if service_tier is None or not model.startswith("openai"):
        return ModelSettings()
    return cast(ModelSettings, {"openai_service_tier": service_tier})


# ---------------------------------------------------------------------------
# Throttling — concurrency + requests-per-minute, read from config at request
# time, keyed by event loop so a fresh ``asyncio.run()`` gets fresh primitives.
# (Same logic that used to monkey-patch ``Model.request``, now in a WrapperModel.)
# ---------------------------------------------------------------------------

_llm_throttle_cache: dict[int, tuple[asyncio.Semaphore | None, AsyncLimiter | None]] = {}
_embedding_throttle_cache: dict[int, tuple[asyncio.Semaphore | None, AsyncLimiter | None]] = {}


def _get_throttles(
    cache: dict[int, tuple[asyncio.Semaphore | None, AsyncLimiter | None]],
    max_concurrency: int | None,
    max_requests_per_minute: int | None,
) -> tuple[asyncio.Semaphore | None, AsyncLimiter | None]:
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in cache:
        sem = asyncio.Semaphore(max_concurrency) if max_concurrency is not None else None
        limiter = AsyncLimiter(max_requests_per_minute, 60) if max_requests_per_minute is not None else None
        cache[loop_id] = (sem, limiter)
    return cache[loop_id]


@asynccontextmanager
async def _throttle(
    cache: dict[int, tuple[asyncio.Semaphore | None, AsyncLimiter | None]],
    max_concurrency: int | None,
    max_rpm: int | None,
) -> AsyncIterator[None]:
    sem, limiter = _get_throttles(cache, max_concurrency, max_rpm)
    async with AsyncExitStack() as stack:
        if sem is not None:
            await stack.enter_async_context(sem)
        if limiter is not None:
            await stack.enter_async_context(limiter)
        yield


@asynccontextmanager
async def embedding_throttle() -> AsyncIterator[None]:
    """Throttle an embedding call (concurrency + RPM from config)."""
    async with _throttle(
        _embedding_throttle_cache,
        tabulaflow_config.max_embedding_concurrency,
        tabulaflow_config.max_embedding_requests_per_minute,
    ):
        yield


class _ThrottledModel(WrapperModel):
    """Gate every model request behind tabulaflow's concurrency + RPM limits."""

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        async with _throttle(
            _llm_throttle_cache,
            tabulaflow_config.max_llm_concurrency,
            tabulaflow_config.max_llm_requests_per_minute,
        ):
            return await self.wrapped.request(messages, model_settings, model_request_parameters)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: Any | None = None,
    ) -> AsyncIterator[Any]:
        async with _throttle(
            _llm_throttle_cache,
            tabulaflow_config.max_llm_concurrency,
            tabulaflow_config.max_llm_requests_per_minute,
        ):
            async with self.wrapped.request_stream(
                messages, model_settings, model_request_parameters, run_context
            ) as stream:
                yield stream


# ---------------------------------------------------------------------------
# <tool_call> parsing — for OpenAI-compatible models (qwen3-coder etc.) that
# emit tool calls as text. Workaround for pydantic-ai issue #2033.
# ---------------------------------------------------------------------------

_TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


class _ToolCallParsingModel(WrapperModel):
    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        response = await self.wrapped.request(messages, model_settings, model_request_parameters)
        new_parts: list[Any] = []
        for part in response.parts:
            if part.part_kind == "text":
                matches = list(_TOOL_CALL_RE.finditer(part.content))
                if matches:
                    try:
                        for match in matches:
                            payload = json.loads(match.group(1).strip())
                            new_parts.append(ToolCallPart(tool_name=payload["name"], args=payload["arguments"]))
                        continue
                    except json.JSONDecodeError:
                        pass
            new_parts.append(part)
        response.parts = new_parts
        return response


# ---------------------------------------------------------------------------
# Base model resolution (incl. Claude on Google Vertex) + the public factory.
# ---------------------------------------------------------------------------


def _build_base(llm: str) -> Model:
    if llm.startswith("google-vertex:claude"):
        import os

        from anthropic import AsyncAnthropicVertex
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(
            llm.split(":", 1)[1],
            provider=AnthropicProvider(
                anthropic_client=AsyncAnthropicVertex(
                    project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
                    region=os.environ["GOOGLE_CLOUD_LOCATION"],
                )
            ),
        )
    return infer_model(llm)


# Resolved base models, cached per event loop (like the throttle caches above). A
# base model owns its provider's ``httpx.AsyncClient`` (connection pool), so reusing
# it means every agent for the same model shares one client instead of leaking a
# fresh, never-closed one per ``make_agent`` call — which otherwise exhausts file
# descriptors under fan-out. Keyed by loop so a client is reused only within the
# loop it is bound to; the per-loop dict maps the model identifier to its base model.
_base_model_cache: dict[int, dict[str, Model]] = {}


def _resolve_base(llm: str | Model) -> Model:
    if isinstance(llm, Model):
        return llm
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        # Resolved outside a running loop (e.g. sync agent construction): no loop
        # to key on, so build a fresh client and let it bind to its first caller's loop.
        return _build_base(llm)
    per_loop = _base_model_cache.setdefault(loop_id, {})
    if llm not in per_loop:
        per_loop[llm] = _build_base(llm)
    return per_loop[llm]


def _make_model(llm: str | Model) -> Model:
    """Wrap a model identifier in tabulaflow's throttle + tool-call parsing."""
    model = _resolve_base(llm)
    if type(model).__name__ == "OpenAIChatModel":  # innermost: post-process the real response
        model = _ToolCallParsingModel(model)
    return _ThrottledModel(model)


class _Agent(Agent):
    """``pydantic_ai.Agent`` that defaults ``usage_limits`` to lift the 50-request
    cap, so ``max_steps`` is the sole governor. Constructed via :func:`make_agent`."""

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("usage_limits", DEFAULT_USAGE_LIMITS)
        return await super().run(*args, **kwargs)

    def run_sync(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("usage_limits", DEFAULT_USAGE_LIMITS)
        return super().run_sync(*args, **kwargs)

    def run_stream(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("usage_limits", DEFAULT_USAGE_LIMITS)
        return super().run_stream(*args, **kwargs)

    def iter(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("usage_limits", DEFAULT_USAGE_LIMITS)
        return super().iter(*args, **kwargs)


_OutputT = TypeVar("_OutputT")


# The common, stable Agent(...) params are named for discoverability + type-checking;
# the long tail (capabilities, deps_type, builtin_tools, ...) flows through **kwargs.
# Deliberately NOT a verbatim copy of Agent.__init__ — that signature is large,
# overloaded, and version-volatile; **kwargs keeps make_agent forward-compatible.
@overload
def make_agent(
    model: str | Model,
    *,
    output_type: type[_OutputT],
    instructions: str | None = None,
    tools: Sequence[Any] = (),
    model_settings: Any = None,
    history_processors: Sequence[Any] | None = None,
    retries: int = 1,
    **kwargs: Any,
) -> Agent[None, _OutputT]: ...
@overload
def make_agent(
    model: str | Model,
    *,
    output_type: ToolOutput[_OutputT],
    instructions: str | None = None,
    tools: Sequence[Any] = (),
    model_settings: Any = None,
    history_processors: Sequence[Any] | None = None,
    retries: int = 1,
    **kwargs: Any,
) -> Agent[None, _OutputT]: ...
@overload
def make_agent(
    model: str | Model,
    *,
    instructions: str | None = None,
    tools: Sequence[Any] = (),
    model_settings: Any = None,
    history_processors: Sequence[Any] | None = None,
    retries: int = 1,
    **kwargs: Any,
) -> Agent[None, str]: ...
def make_agent(
    model: str | Model,
    *,
    output_type: Any = str,
    instructions: str | None = None,
    tools: Sequence[Any] = (),
    model_settings: Any = None,
    history_processors: Sequence[Any] | None = None,
    retries: int = 1,
    **kwargs: Any,
) -> Agent[Any, Any]:
    """Build a pydantic-ai Agent wired with tabulaflow's defaults.

    The model is wrapped with throttling / ``<tool_call>`` parsing / vertex-claude
    resolution, and runs default to ``usage_limits=DEFAULT_USAGE_LIMITS`` (no
    50-request cap). Every tabulaflow ``Agent`` should be built via this. The named
    params are the commonly-used ones (for discovery + type-checking); any other
    keyword accepted by :class:`pydantic_ai.Agent` (e.g. ``capabilities``,
    ``deps_type``) flows through ``**kwargs``.
    """
    ensure_global_setup()
    if history_processors is not None:
        # pydantic-ai ≥1.107 deprecates Agent(history_processors=...) in favor of
        # ProcessHistory capabilities; adapt here so callers keep the stable kwarg.
        from pydantic_ai.capabilities import ProcessHistory

        kwargs["capabilities"] = [*kwargs.get("capabilities", ()), *(ProcessHistory(p) for p in history_processors)]
    return _Agent(
        _make_model(model),
        output_type=output_type,
        instructions=instructions,
        tools=tools,
        model_settings=model_settings,
        retries=retries,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Process-global setup (was patches.setup(); invoked once from configure()).
# ---------------------------------------------------------------------------


def register_custom_model_prices() -> None:
    """Register pricing for models not yet in litellm's bundled data."""
    import litellm

    custom_prices = {
        "gpt-5.4-mini": {
            "input_cost_per_token": 7.5e-07,
            "output_cost_per_token": 4.5e-06,
            "max_input_tokens": 400000,
            "max_output_tokens": 128000,
            "max_tokens": 128000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
    }
    for model, info in custom_prices.items():
        if model not in litellm.model_cost:
            litellm.model_cost[model] = info


def disable_bigquery_tracing() -> None:
    """Disable BigQuery's built-in OpenTelemetry tracing (noisy in our traces)."""
    try:
        from google.cloud.bigquery import opentelemetry_tracing

        opentelemetry_tracing.HAS_OPENTELEMETRY = False
    except ImportError:
        pass


_global_setup_done = False


def ensure_global_setup() -> None:
    """Run process-global LLM setup (custom model prices + optional BigQuery-tracing
    suppression) exactly once.

    Deferred out of ``configure()`` and invoked lazily by ``make_agent``: registering
    prices imports litellm (~1s), so doing it eagerly at ``configure()`` blocked app
    startup before the first banner. It now runs when the first agent is built —
    which for the TUI is in the background session worker, off the UI thread."""
    global _global_setup_done
    if _global_setup_done:
        return
    _global_setup_done = True
    register_custom_model_prices()
    from tabulaflow.core.config import tabulaflow_config

    if tabulaflow_config.disable_bigquery_tracing:
        disable_bigquery_tracing()
