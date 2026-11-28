"""Interactive app launcher."""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum
import os
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
    from tabulaflow.app.credentials import activate_vllm_connection, load_saved_api_keys

    config = load_app_config()
    overridden = load_saved_api_keys(preferences=config.credential_preferences)
    endpoint = config.endpoint_connections.get("vllm")
    if endpoint is not None and endpoint.source == "saved":
        overridden.setdefault("VLLM_BASE_URL", os.getenv("VLLM_BASE_URL", ""))
        overridden.setdefault("VLLM_API_KEY", os.getenv("VLLM_API_KEY", ""))
        preference = config.credential_preferences.get("vllm")
        api_key = os.getenv("VLLM_API_KEY", "") if preference is not None and preference.source == "saved" else ""
        activate_vllm_connection(endpoint.base_url, api_key)
    return replace(resolve_llm_config(config), environment_variables=overridden)


def run_chat(
    *,
    llm_service_tier: AppLLMServiceTier = AppLLMServiceTier.DEFAULT,
    enable_schema_cache: bool = False,
    log_level: AppLogLevel = AppLogLevel.INFO,
    browser_pane_port: int | None = None,
    browser_pane_host: str = "127.0.0.1",
    browser_pane_public_url: str | None = None,
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
            browser_pane_host=browser_pane_host,
            browser_pane_port=browser_pane_port,
            browser_pane_public_url=browser_pane_public_url,
        )
    )
