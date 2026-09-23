"""Interactive app launcher."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from tabulaflow.app.config import ResolvedLLMConfig

if TYPE_CHECKING:
    from tabulaflow.agents import AgentRuntimeConfig


class AppLLMServiceTier(StrEnum):
    """Service tiers intentionally exposed by the interactive app."""

    DEFAULT = "default"
    PRIORITY = "priority"


class AppLogLevel(StrEnum):
    """Operational log levels exposed by the interactive app."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def _app_agent_runtime_config(max_llm_requests_per_minute: int = 300) -> AgentRuntimeConfig:
    """Return agent policy that keeps interactive sessions cache-free."""
    from tabulaflow.agents import AgentRuntimeConfig

    from tabulaflow.app.config import APP_MAX_LLM_CONCURRENCY

    return AgentRuntimeConfig(
        preprocessing_cache_mode="off",
        max_llm_concurrency=APP_MAX_LLM_CONCURRENCY,
        max_llm_requests_per_minute=max_llm_requests_per_minute,
    )


def _resolve_startup_llm_config() -> ResolvedLLMConfig:
    from tabulaflow.app.config import load_app_config, resolve_llm_config

    return resolve_llm_config(load_app_config())


def run_chat(
    *,
    llm_service_tier: AppLLMServiceTier = AppLLMServiceTier.DEFAULT,
    enable_schema_cache: bool = False,
    log_level: AppLogLevel = AppLogLevel.INFO,
    output_pane_port: int | None = None,
    output_pane_host: str = "127.0.0.1",
    output_pane_public_url: str | None = None,
) -> None:
    """Start an interactive data session."""
    import asyncio
    import logging

    startup_llm = _resolve_startup_llm_config()

    logging.basicConfig(level=logging.WARNING)

    from tabulaflow.agents import initialize_agent_runtime
    from tabulaflow.app.tui import run_tui

    initialize_agent_runtime(_app_agent_runtime_config(startup_llm.requests_per_minute))
    asyncio.run(
        run_tui(
            llm_config=startup_llm,
            llm_service_tier=llm_service_tier.value,
            enable_schema_cache=enable_schema_cache,
            log_level=getattr(logging, log_level.name),
            output_pane_host=output_pane_host,
            output_pane_port=output_pane_port,
            output_pane_public_url=output_pane_public_url,
        )
    )
