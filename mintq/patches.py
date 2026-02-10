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
from mintq.config import config


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

_llm_semaphore = asyncio.Semaphore(config.max_llm_concurrency) if config.max_llm_concurrency is not None else None
_llm_rate_limit = (
    AsyncLimiter(config.max_llm_requests_per_minute, 60) if config.max_llm_requests_per_minute is not None else None
)


async def _throttled_request(self: Model, *args: Any, **kwargs: Any) -> Any:
    """
    Wraps Model.request() with semaphore throttling based on max_llm_concurrency in config.
    """
    async with AsyncExitStack() as stack:
        if _llm_semaphore is not None:
            await stack.enter_async_context(_llm_semaphore)
        if _llm_rate_limit is not None:
            await stack.enter_async_context(_llm_rate_limit)
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

_embedding_semaphore = (
    asyncio.Semaphore(config.max_embedding_concurrency) if config.max_embedding_concurrency is not None else None
)
_embedding_rate_limit = (
    AsyncLimiter(config.max_embedding_requests_per_minute, 60)
    if config.max_embedding_requests_per_minute is not None
    else None
)


async def _throttled_embed(self: EmbeddingModel, *args: Any, **kwargs: Any) -> Any:
    """
    Wraps EmbeddingModel.embed() with semaphore throttling based on max_embedding_concurrency in config.
    """
    async with AsyncExitStack() as stack:
        if _embedding_semaphore is not None:
            await stack.enter_async_context(_embedding_semaphore)
        if _embedding_rate_limit is not None:
            await stack.enter_async_context(_embedding_rate_limit)
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
