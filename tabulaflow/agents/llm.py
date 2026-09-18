"""LLM model factory.

Every pydantic-ai ``Agent`` in tabulaflow is built through :func:`make_agent`,
so concurrency/RPM throttling and Claude-on-Vertex resolution apply *by
construction*. This replaces the global monkey-patches that used to live in
``patches.py`` (which hijacked ``pydantic_ai.models.infer_model`` and
``Model.request`` process-wide). Importing this module has no side effects.

Agents built through :func:`make_agent` lift pydantic-ai's default 50-request
cap so multi-step tool loops can continue.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncIterator, TypeVar, cast, overload

from aiolimiter import AsyncLimiter
from pydantic_ai import Agent, ToolOutput, UsageLimits
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters, infer_model
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.profiles.anthropic import (
    ANTHROPIC_THINKING_BUDGET_MAP,
    anthropic_model_profile,
)
from pydantic_ai.settings import (
    ModelSettings,
    ServiceTier as ServiceTier,
    ThinkingEffort as ReasoningEffort,
    ThinkingLevel as ReasoningLevel,
)

from tabulaflow.agents.runtime import _get_agent_runtime

__all__ = [
    "ReasoningEffort",
    "ReasoningLevel",
    "ServiceTier",
    "embedding_throttle",
    "make_agent",
    "make_model_settings",
    "model_label",
    "uses_openai_responses",
]

_DEFAULT_USAGE_LIMITS = UsageLimits(request_limit=None)

_ANTHROPIC_ANSWER_TOKEN_HEADROOM = 8192


def model_label(model: str) -> str:
    """Remove a provider prefix and trailing release date from a model identifier.

    Examples:
        ``openai:gpt-5.6-sol`` becomes ``gpt-5.6-sol``.
        ``openai:gpt-5-2025-08-07`` becomes ``gpt-5``.
        ``anthropic:claude-sonnet-4-5-20250929`` becomes
        ``claude-sonnet-4-5``.
    """
    _, separator, name = model.partition(":")
    return re.sub(r"-(?:\d{4}-\d{2}-\d{2}|\d{8})$", "", name if separator else model)


def uses_openai_responses(model: str) -> bool:
    """Whether a model identifier selects Pydantic AI's OpenAI Responses model."""
    provider, _, _ = model.partition(":")
    return provider in {"openai", "openai-responses"}


def make_model_settings(
    *,
    model: str,
    reasoning: ReasoningLevel | None = None,
    service_tier: ServiceTier | None = None,
    timeout: float | None = None,
) -> ModelSettings:
    """Build pydantic-ai model settings from provider-neutral LLM config.

    Args:
        model: Provider-qualified model identifier (e.g. ``anthropic:claude-...``).
        reasoning: Unified thinking level, translated per provider.
        service_tier: Provider service tier, for providers that expose one.
        timeout: Per-request timeout in seconds. On timeout the provider SDK
            retries the request automatically, so this doubles as a hang
            watchdog for non-streaming calls.
    """
    return cast(
        ModelSettings,
        {
            **_reasoning_model_settings(reasoning, model=model),
            **_anthropic_token_settings(reasoning, model=model),
            **({} if service_tier is None else {"service_tier": service_tier}),
            **({} if timeout is None else {"timeout": timeout}),
        },
    )


def _reasoning_model_settings(reasoning: ReasoningLevel | None, *, model: str) -> ModelSettings:
    """Return provider-specific reasoning settings.

    ``pydantic-ai`` uses ``thinking`` as the provider-neutral reasoning knob.
    OpenAI Responses models get detailed reasoning summaries whenever thinking
    is enabled.
    """
    if reasoning is None:
        return ModelSettings()
    settings = ModelSettings(thinking=reasoning)
    if reasoning is not False and uses_openai_responses(model):
        settings = cast(ModelSettings, {**settings, "openai_reasoning_summary": "detailed"})
    return settings


def _anthropic_token_settings(reasoning: ReasoningLevel | None, *, model: str) -> ModelSettings:
    """Give budget-thinking Claude models enough output tokens for thinking and an answer."""
    if reasoning is None or reasoning is False:
        return ModelSettings()
    if model.startswith("anthropic:") or model.startswith("google-cloud:claude"):
        model_name = model.split(":", 1)[1]
    else:
        return ModelSettings()

    profile = anthropic_model_profile(model_name)
    if profile is not None and profile.get("anthropic_supports_adaptive_thinking", False):
        return ModelSettings()
    budget = ANTHROPIC_THINKING_BUDGET_MAP.get(cast(Any, reasoning))
    if budget is None:
        return ModelSettings()
    return ModelSettings(max_tokens=budget + _ANTHROPIC_ANSWER_TOKEN_HEADROOM)


# ---------------------------------------------------------------------------
# Throttling — concurrency + requests-per-minute, with per-event-loop primitives
# owned by the process-wide agent runtime.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _throttle(
    throttles: tuple[asyncio.Semaphore | None, AsyncLimiter | None],
) -> AsyncIterator[None]:
    sem, limiter = throttles
    async with AsyncExitStack() as stack:
        if sem is not None:
            await stack.enter_async_context(sem)
        if limiter is not None:
            await stack.enter_async_context(limiter)
        yield


@asynccontextmanager
async def embedding_throttle() -> AsyncIterator[None]:
    """Throttle an embedding call (concurrency + RPM from config)."""
    async with _throttle(_get_agent_runtime().embedding_throttles()):
        yield


class _ThrottledModel(WrapperModel):
    """Gate every model request behind tabulaflow's concurrency + RPM limits."""

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        async with _throttle(_get_agent_runtime().llm_throttles()):
            return await self.wrapped.request(messages, model_settings, model_request_parameters)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: Any | None = None,
    ) -> AsyncIterator[Any]:
        async with _throttle(_get_agent_runtime().llm_throttles()):
            async with self.wrapped.request_stream(
                messages, model_settings, model_request_parameters, run_context
            ) as stream:
                yield stream


# ---------------------------------------------------------------------------
# Base model resolution (incl. Claude on Google Vertex) + the public factory.
# ---------------------------------------------------------------------------


def _build_base(llm: str) -> Model:
    if llm.startswith("google-cloud:claude"):
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


# Resolved base models are cached per event loop by the agent runtime. A
# base model owns its provider's ``httpx.AsyncClient`` (connection pool), so reusing
# it means every agent for the same model shares one client instead of leaking a
# fresh, never-closed one per ``make_agent`` call — which otherwise exhausts file
# descriptors under fan-out. Keyed by loop so a client is reused only within the
# loop it is bound to; the per-loop dict maps the model identifier to its base model.
def _resolve_base(llm: str | Model) -> Model:
    if isinstance(llm, Model):
        return llm
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Resolved outside a running loop (e.g. sync agent construction): no loop
        # to key on, so build a fresh client and let it bind to its first caller's loop.
        return _build_base(llm)
    return _get_agent_runtime().get_base_model(llm, lambda: _build_base(llm))


def _make_model(llm: str | Model) -> Model:
    """Wrap a model identifier in tabulaflow's request throttling."""
    return _ThrottledModel(_resolve_base(llm))


class _Agent(Agent):
    """``pydantic_ai.Agent`` configured for unlimited multi-step runs."""

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get("usage_limits") is None:
            kwargs["usage_limits"] = _DEFAULT_USAGE_LIMITS
        return await super().run(*args, **kwargs)

    def run_sync(self, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get("usage_limits") is None:
            kwargs["usage_limits"] = _DEFAULT_USAGE_LIMITS
        return super().run_sync(*args, **kwargs)

    def run_stream(self, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get("usage_limits") is None:
            kwargs["usage_limits"] = _DEFAULT_USAGE_LIMITS
        return super().run_stream(*args, **kwargs)

    def iter(self, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get("usage_limits") is None:
            kwargs["usage_limits"] = _DEFAULT_USAGE_LIMITS
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
    retries: int = 3,
    **kwargs: Any,
) -> Agent[object, _OutputT]: ...
@overload
def make_agent(
    model: str | Model,
    *,
    output_type: ToolOutput[_OutputT],
    instructions: str | None = None,
    tools: Sequence[Any] = (),
    model_settings: Any = None,
    retries: int = 3,
    **kwargs: Any,
) -> Agent[object, _OutputT]: ...
@overload
def make_agent(
    model: str | Model,
    *,
    instructions: str | None = None,
    tools: Sequence[Any] = (),
    model_settings: Any = None,
    retries: int = 3,
    **kwargs: Any,
) -> Agent[object, str]: ...
def make_agent(
    model: str | Model,
    *,
    output_type: Any = str,
    instructions: str | None = None,
    tools: Sequence[Any] = (),
    model_settings: Any = None,
    retries: int = 3,
    **kwargs: Any,
) -> Agent[Any, Any]:
    """Build a pydantic-ai Agent wired with tabulaflow's defaults.

    The model is wrapped with throttling and vertex-claude resolution, and runs
    default to no request limit. Every
    tabulaflow ``Agent`` should be built via this. The named params are the
    commonly-used ones (for discovery + type-checking); any other keyword accepted
    by :class:`pydantic_ai.Agent` (e.g. ``capabilities``, ``deps_type``) flows
    through ``**kwargs``.
    """
    return _Agent(
        _make_model(model),
        output_type=output_type,
        instructions=instructions,
        tools=tools,
        model_settings=model_settings,
        retries=retries,
        **kwargs,
    )
