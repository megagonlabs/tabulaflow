"""
Monkey patches for third-party libraries.

This module applies runtime patches to external libraries to add custom functionality.
Import this module to ensure patches are applied.
"""
import asyncio
from pydantic_ai import Agent
from mintq.config import config


# Initialize semaphore for throttling pydantic_ai Agent.run() calls
if config.max_llm_concurrency is not None:
    _llm_semaphore = asyncio.Semaphore(config.max_llm_concurrency)
else:
    _llm_semaphore = None


async def _throttled_run(self, *args, **kwargs):
    """Throttled version of Agent.run() that respects max_llm_concurrency."""
    semaphore = _llm_semaphore
    orig_run = Agent.__original_run__
    if semaphore is not None:
        async with semaphore:
            return await orig_run(self, *args, **kwargs)
    return await orig_run(self, *args, **kwargs)


# Apply the patch to Agent.run()
if not hasattr(Agent, "__original_run__"):
    Agent.__original_run__ = Agent.run
    Agent.run = _throttled_run
