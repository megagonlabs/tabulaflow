"""
Monkey patches for third-party libraries.

This module applies runtime patches to external libraries to add custom functionality.
Import this module to ensure patches are applied.
"""

import asyncio
from contextlib import AsyncExitStack
from typing import Any, Callable
import os
import re
from anthropic import AsyncAnthropicVertex
import json
from aiolimiter import AsyncLimiter
import pydantic_ai.models
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models import KnownModelName, Model, ModelRequestParameters
from pydantic_ai.providers import Provider, infer_provider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.messages import ModelResponse, ModelMessage, ToolCallPart
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.embeddings.base import EmbeddingModel
from pydantic_ai.usage import UsageLimits
from mintq.config import mintq_config


# =====================================================================================
# |     Disable the default pydantic_ai request_limit of 50.                         |
# |     Step limiting is handled by max_steps_processor in agenthub/utils.py instead. |
# =====================================================================================

UsageLimits.__init__.__kwdefaults__["request_limit"] = None  # type: ignore[index]


# =====================================================================================================
# |     Patch Model.request to support parsing output with <tool_call> tags (e.g. for qwen3-coder)    |
# |     (temporary fix until https://github.com/pydantic/pydantic-ai/issues/2033 is fixed)            |
# =====================================================================================================


async def _patched_request(
    self: OpenAIChatModel,
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse:
    response = await self.__original_openai_request__(messages, model_settings, model_request_parameters)  # type: ignore
    try:
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


if not hasattr(OpenAIChatModel, "__original_openai_request__"):
    OpenAIChatModel.__original_openai_request__ = OpenAIChatModel.request  # type: ignore
    OpenAIChatModel.request = _patched_request  # type: ignore


# =============================================================================================
# |     Patch pydantic_ai.models.infer_model to support Claude models in Google Vertex AI     |
# |     (temporary fix until https://github.com/pydantic/pydantic-ai/pull/1392 is fixed)      |
# =============================================================================================


def get_anthropic_vertex_model(model_name: str) -> Model:
    """Adpapted from https://github.com/pydantic/pydantic-ai/pull/1392#issuecomment-2851287096"""
    return AnthropicModel(
        model_name,
        provider=AnthropicProvider(
            anthropic_client=AsyncAnthropicVertex(
                project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
                region=os.environ["GOOGLE_CLOUD_LOCATION"],
            )
        ),
    )


_original_infer_model = pydantic_ai.models.infer_model


def _patched_infer_model(  # noqa: C901
    model: Model | KnownModelName | str, provider_factory: Callable[[str], Provider[Any]] = infer_provider
) -> Model:
    if isinstance(model, str) and model.startswith("google-vertex:claude"):
        return get_anthropic_vertex_model(model.split(":")[1])
    return _original_infer_model(model)


pydantic_ai.models.infer_model = _patched_infer_model


# ==========================================================================================
# |     Patch pydantic_ai.models.Model.request() to support max concurrency throttling     |
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


async def _throttled_request(self: Model, *args: Any, **kwargs: Any) -> Any:
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
        return await self.__original_request__(*args, **kwargs)  # type: ignore


def patch_model_class(model_class: type[Model]) -> None:
    if not hasattr(model_class, "__original_request__"):
        model_class.__original_request__ = model_class.request  # type: ignore
        model_class.request = _throttled_request  # type: ignore


def patch_all_models() -> None:
    from pydantic_ai.models.cohere import CohereModel
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.models.groq import GroqModel
    from pydantic_ai.models.mistral import MistralModel
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.models.bedrock import BedrockConverseModel
    from pydantic_ai.models.huggingface import HuggingFaceModel

    all_model_classes: list[type[Model]] = [
        CohereModel,
        OpenAIChatModel,
        OpenAIResponsesModel,
        GoogleModel,
        GroqModel,
        MistralModel,
        AnthropicModel,
        BedrockConverseModel,
        HuggingFaceModel,
    ]
    for model_class in all_model_classes:
        patch_model_class(model_class)


patch_all_models()


# ================================================================================================
# |     Patch pydantic_ai embedding models to support max concurrency and rate limit throttling  |
# ================================================================================================


async def _throttled_embed(self: EmbeddingModel, *args: Any, **kwargs: Any) -> Any:
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
        return await self.__original_embed__(*args, **kwargs)  # type: ignore


def patch_embedding_model_class(model_class: type[EmbeddingModel]) -> None:
    if not hasattr(model_class, "__original_embed__"):
        model_class.__original_embed__ = model_class.embed  # type: ignore
        model_class.embed = _throttled_embed  # type: ignore


def patch_all_embedding_models() -> None:
    from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
    from pydantic_ai.embeddings.cohere import CohereEmbeddingModel
    from pydantic_ai.embeddings.google import GoogleEmbeddingModel
    from pydantic_ai.embeddings.bedrock import BedrockEmbeddingModel

    all_embedding_model_classes: list[type[EmbeddingModel]] = [
        OpenAIEmbeddingModel,
        CohereEmbeddingModel,
        GoogleEmbeddingModel,
        BedrockEmbeddingModel,
    ]
    for model_class in all_embedding_model_classes:
        patch_embedding_model_class(model_class)


patch_all_embedding_models()


# ================================================================================================
# |     Disable BigQuery's built-in OpenTelemetry tracing                                        |
# |     The google-cloud-bigquery client auto-emits OTEL spans when it detects a TracerProvider.  |
# |     This pollutes Langfuse with low-level DB spans. There's no env var to disable it, so we   |
# |     flip the HAS_OPENTELEMETRY flag to make its create_span() yield None.                     |
# ================================================================================================

if mintq_config.disable_bigquery_tracing:
    try:
        from google.cloud.bigquery import opentelemetry_tracing

        opentelemetry_tracing.HAS_OPENTELEMETRY = False
    except ImportError:
        pass
