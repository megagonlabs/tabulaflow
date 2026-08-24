"""Agent runtime, reusable chat sessions, tools, and LLM-powered modules."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.chat.session import ChatSession
    from tabulaflow.agents.config import AgentRuntimeConfig
    from tabulaflow.agents.observability import instrument_agents
    from tabulaflow.agents.runtime import initialize_agent_runtime

_LAZY_EXPORTS = {
    "AgentRuntimeConfig": ("tabulaflow.agents.config", "AgentRuntimeConfig"),
    "ChatSession": ("tabulaflow.agents.chat", "ChatSession"),
    "initialize_agent_runtime": ("tabulaflow.agents.runtime", "initialize_agent_runtime"),
    "instrument_agents": ("tabulaflow.agents.observability", "instrument_agents"),
}

__all__ = ["AgentRuntimeConfig", "ChatSession", "initialize_agent_runtime", "instrument_agents"]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})
