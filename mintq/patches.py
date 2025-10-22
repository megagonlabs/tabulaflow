"""
Monkey patches for third-party libraries.

This module applies runtime patches to external libraries to add custom functionality.
Import this module to ensure patches are applied.
"""

import asyncio
from typing import Any
import os
from anthropic import AsyncAnthropicVertex
from pydantic_ai import Agent
import pydantic_ai.models
from pydantic_ai.models import KnownModelName, Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from mintq.config import config

# =============================================================================================
# |     Patch pydantic_ai.models.infer_model to support Claude models in Google Vertex AI     |
# =============================================================================================



def get_anthropic_vertex_model(model_name: str) -> Model:
    """Adpapted from https://github.com/pydantic/pydantic-ai/pull/1392#issuecomment-2851287096"""
    return AnthropicModel(
        model_name,
        provider=AnthropicProvider(  # type: ignore
            anthropic_client=AsyncAnthropicVertex(
                project_id=os.environ["VERTEXAI_PROJECT"],
                region=os.environ["VERTEXAI_LOCATION"],
            )
        ),
    )


_original_infer_model = pydantic_ai.models.infer_model


def _patched_infer_model(model: Model | KnownModelName | str) -> Model:
    if isinstance(model, str) and model.startswith("google-vertex:claude"):
        return get_anthropic_vertex_model(model.split(":")[1])
    return _original_infer_model(model)


pydantic_ai.models.infer_model = _patched_infer_model

# ===============================================================================
# |     Patch pydantic_ai.Agent.run() to support max concurrency throttling     |
# ===============================================================================

_llm_semaphore = asyncio.Semaphore(config.max_llm_concurrency) if config.max_llm_concurrency is not None else None


async def _throttled_run(self: Agent, *args: Any, **kwargs: Any) -> Any:
    """
    Wraps Agent.run() with semaphore throttling based on max_llm_concurrency in config.
    """
    semaphore = _llm_semaphore
    orig_run = Agent.__original_run__  # type: ignore
    if semaphore is not None:
        async with semaphore:
            return await orig_run(self, *args, **kwargs)
    else:
        return await orig_run(self, *args, **kwargs)


# Apply the patch to Agent.run()
if not hasattr(Agent, "__original_run__"):
    Agent.__original_run__ = Agent.run  # type: ignore
    Agent.run = _throttled_run  # type: ignore
