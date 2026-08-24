"""Agent runtime, reusable chat sessions, tools, and LLM-powered modules."""

from typing import TYPE_CHECKING

from tabulaflow.agents.config import AgentRuntimeConfig
from tabulaflow.agents.runtime import initialize_agent_runtime

if TYPE_CHECKING:
    from tabulaflow.agents.chat import ChatSession


def __getattr__(name: str) -> object:
    if name == "ChatSession":
        from tabulaflow.agents.chat import ChatSession

        return ChatSession
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AgentRuntimeConfig", "ChatSession", "initialize_agent_runtime"]
