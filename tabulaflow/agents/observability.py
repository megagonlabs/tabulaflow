"""Explicit observability setup for agent execution."""

import threading

from pydantic_ai import Agent

_instrumented = False
_instrument_lock = threading.Lock()


def instrument_agents() -> None:
    """Enable Pydantic AI instrumentation once for this process."""
    global _instrumented
    if _instrumented:
        return
    with _instrument_lock:
        if not _instrumented:
            Agent.instrument_all()
            _instrumented = True


__all__ = ["instrument_agents"]
