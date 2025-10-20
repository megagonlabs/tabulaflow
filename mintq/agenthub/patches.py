"""
Monkey patches for third-party libraries.

This module applies runtime patches to external libraries to add custom functionality.
Import this module to ensure patches are applied.
"""

import asyncio
from typing import Any
from pydantic_ai import Agent
from mintq.config import config


# Create a semaphore for throttling Agent.run() calls, if concurrency is limited.
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
