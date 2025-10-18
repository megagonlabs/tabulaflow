"""
Monkey patches for third-party libraries.

This module applies runtime patches to external libraries to add custom functionality.
Import this module to ensure patches are applied.
"""
import asyncio
from pydantic_ai import Agent
from mintq.config import config


# Initialize semaphore for throttling pydantic_ai Agent.run() calls
if config.max_pydantic_ai_agent_concurrency is not None:
    _pydantic_ai_agent_semaphore = asyncio.Semaphore(config.max_pydantic_ai_agent_concurrency)
else:
    _pydantic_ai_agent_semaphore = None


async def _throttled_run(self, *args, **kwargs):
    """Throttled version of Agent.run() that respects max_pydantic_ai_agent_concurrency."""
    semaphore = _pydantic_ai_agent_semaphore
    orig_run = Agent.__original_run__
    if semaphore is not None:
        async with semaphore:
            print("Entered semaphore")
            return await orig_run(self, *args, **kwargs)
    print("Not entered semaphore")
    return await orig_run(self, *args, **kwargs)


# Apply the patch to Agent.run()
if not hasattr(Agent, "__original_run__"):
    Agent.__original_run__ = Agent.run
    Agent.run = _throttled_run
