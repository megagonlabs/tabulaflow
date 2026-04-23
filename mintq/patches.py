"""
Monkey patches for third-party libraries.

This module applies runtime patches to external libraries to add custom functionality.
Import this module to ensure patches are applied.

Provider-specific imports are deferred to avoid pulling in every SDK at import time.
Patches are applied lazily when models are first resolved via ``infer_model``.
"""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import AsyncExitStack
from typing import Any, TYPE_CHECKING

from aiolimiter import AsyncLimiter
import pydantic_ai.models
from pydantic_ai.usage import UsageLimits

from mintq.config import mintq_config

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage, ModelResponse
    from pydantic_ai.models import ModelRequestParameters
    from pydantic_ai.settings import ModelSettings


# =====================================================================================
# |     Disable the default pydantic_ai request_limit of 50.                         |
# |     Step limiting is handled by max_steps_processor in agenthub/utils.py instead. |
# =====================================================================================

UsageLimits.__init__.__kwdefaults__["request_limit"] = None  # type: ignore[index]


# ==========================================================================================
# |     Throttling infrastructure                                                          |
# ==========================================================================================

_llm_throttle_cache: dict[int, tuple[asyncio.Semaphore | None, AsyncLimiter | None]] = {}
_embedding_throttle_cache: dict[int, tuple[asyncio.Semaphore | None, AsyncLimiter | None]] = {}


def _get_throttles(
    cache: dict[int, tuple[asyncio.Semaphore | None, AsyncLimiter | None]],
    max_concurrency: int | None,
    max_requests_per_minute: int | None,
) -> tuple[asyncio.Semaphore | None, AsyncLimiter | None]:
    """Return (semaphore, rate_limiter) bound to the current event loop.

    Creates fresh instances when called from a new loop (e.g. a second
    ``asyncio.run()`` call), so callers never hit "attached to a different
    loop" errors.
    """
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in cache:
        sem = asyncio.Semaphore(max_concurrency) if max_concurrency is not None else None
        limiter = AsyncLimiter(max_requests_per_minute, 60) if max_requests_per_minute is not None else None
        cache[loop_id] = (sem, limiter)
    return cache[loop_id]


async def _throttled_request(self: Any, *args: Any, **kwargs: Any) -> Any:
    """Wraps Model.request() with concurrency and rate-limit throttling."""
    sem, limiter = _get_throttles(
        _llm_throttle_cache,
        mintq_config.max_llm_concurrency,
        mintq_config.max_llm_requests_per_minute,
    )
    async with AsyncExitStack() as stack:
        if sem is not None:
            await stack.enter_async_context(sem)
        if limiter is not None:
            await stack.enter_async_context(limiter)
        return await self.__original_request__(*args, **kwargs)


async def _throttled_embed(self: Any, *args: Any, **kwargs: Any) -> Any:
    """Wraps EmbeddingModel.embed() with concurrency and rate-limit throttling."""
    sem, limiter = _get_throttles(
        _embedding_throttle_cache,
        mintq_config.max_embedding_concurrency,
        mintq_config.max_embedding_requests_per_minute,
    )
    async with AsyncExitStack() as stack:
        if sem is not None:
            await stack.enter_async_context(sem)
        if limiter is not None:
            await stack.enter_async_context(limiter)
        return await self.__original_embed__(*args, **kwargs)


# =====================================================================================================
# |     Patch Model.request to support parsing output with <tool_call> tags (e.g. for qwen3-coder)    |
# |     (temporary fix until https://github.com/pydantic/pydantic-ai/issues/2033 is fixed)            |
# =====================================================================================================


async def _patched_openai_request(
    self: Any,
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse:
    response = await self.__original_openai_request__(messages, model_settings, model_request_parameters)
    try:
        from pydantic_ai.messages import ToolCallPart

        new_parts = []
        for part in response.parts:
            if part.part_kind == "text":
                tool_call_pattern = r"<tool_call>(.*?)</tool_call>"
                matches = list(re.finditer(tool_call_pattern, part.content, re.DOTALL))

                if matches:
                    for match in matches:
                        content = match.group(1).strip()
                        payload = json.loads(content)
                        new_parts.append(
                            ToolCallPart(
                                tool_name=payload["name"],
                                args=payload["arguments"],
                            )
                        )
                    continue
            new_parts.append(part)
        response.parts = new_parts
    except json.JSONDecodeError:
        pass
    return response  # type: ignore


# ==========================================================================================
# |     Lazy per-class patching                                                            |
# ==========================================================================================

_patched_model_classes: set[type] = set()


def _patch_model_class(model_cls: type) -> None:
    """Apply throttling (and OpenAI tool_call parsing) to a model class on first use."""
    if model_cls in _patched_model_classes:
        return
    _patched_model_classes.add(model_cls)

    # OpenAI: parse <tool_call> tags (for qwen3-coder etc.)
    if model_cls.__name__ == "OpenAIChatModel":
        if not hasattr(model_cls, "__original_openai_request__"):
            model_cls.__original_openai_request__ = model_cls.request  # type: ignore
            model_cls.request = _patched_openai_request  # type: ignore

    # Throttling for all model classes
    if not hasattr(model_cls, "__original_request__"):
        model_cls.__original_request__ = model_cls.request  # type: ignore
        model_cls.request = _throttled_request  # type: ignore


# ==========================================================================================
# |     One-time deferred setup (runs on first model resolution)                           |
# ==========================================================================================

_full_setup_done = False


def setup() -> None:
    """Apply deferred patches: embedding throttling, BigQuery tracing, litellm prices.

    Called from ``mintq.configure()`` for pipeline runs. Not needed for the CLI.
    """
    global _full_setup_done
    if _full_setup_done:
        return
    _full_setup_done = True

    # Patch all embedding model classes
    from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
    from pydantic_ai.embeddings.cohere import CohereEmbeddingModel
    from pydantic_ai.embeddings.google import GoogleEmbeddingModel
    from pydantic_ai.embeddings.bedrock import BedrockEmbeddingModel

    for cls in (OpenAIEmbeddingModel, CohereEmbeddingModel, GoogleEmbeddingModel, BedrockEmbeddingModel):
        if not hasattr(cls, "__original_embed__"):
            cls.__original_embed__ = cls.embed  # type: ignore
            cls.embed = _throttled_embed  # type: ignore

    # Disable BigQuery's built-in OpenTelemetry tracing
    if mintq_config.disable_bigquery_tracing:
        try:
            from google.cloud.bigquery import opentelemetry_tracing

            opentelemetry_tracing.HAS_OPENTELEMETRY = False
        except ImportError:
            pass

    # Register custom model prices in litellm
    _register_custom_model_prices()


def _register_custom_model_prices() -> None:
    """Register pricing for models not yet in litellm's bundled data.

    Entries are skipped if litellm already has them, so this is safe
    to leave in place after litellm adds native support.
    """
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


# =============================================================================================
# |     Patch pydantic_ai.models.infer_model                                                  |
# |     - Support Claude models in Google Vertex AI                                           |
# |     - Lazily apply throttling and model-specific patches on first use                     |
# =============================================================================================

_original_infer_model = pydantic_ai.models.infer_model


def _patched_infer_model(model: Any, *args: Any, **kwargs: Any) -> Any:
    result: Any
    if isinstance(model, str) and model.startswith("google-vertex:claude"):
        import os

        from anthropic import AsyncAnthropicVertex
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        result = AnthropicModel(
            model.split(":")[1],
            provider=AnthropicProvider(
                anthropic_client=AsyncAnthropicVertex(
                    project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
                    region=os.environ["GOOGLE_CLOUD_LOCATION"],
                )
            ),
        )
    else:
        result = _original_infer_model(model, *args, **kwargs)

    _patch_model_class(type(result))
    return result


pydantic_ai.models.infer_model = _patched_infer_model
