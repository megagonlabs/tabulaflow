"""Interactive app launcher."""

from enum import StrEnum

import typer

from tabulaflow.app.config import ResolvedLLMSelection


class AppServiceTier(StrEnum):
    """Service tiers intentionally exposed by the interactive app."""

    DEFAULT = "default"
    PRIORITY = "priority"


def _resolve_startup_llm_selection(*, llm_preset: str | None) -> ResolvedLLMSelection:
    from tabulaflow.app.config import load_app_config, resolve_llm_selection

    try:
        return resolve_llm_selection(load_app_config(), override=llm_preset)
    except ValueError as e:
        raise typer.BadParameter(str(e), param_hint="--llm-preset") from None


def run_chat(
    *,
    llm_preset: str | None = None,
    service_tier: AppServiceTier = AppServiceTier.DEFAULT,
    output_pane_port: int | None = None,
    output_pane_host: str = "127.0.0.1",
    output_pane_public_url: str | None = None,
) -> None:
    """Start an interactive database chat session."""
    import asyncio
    import logging

    startup_llm = _resolve_startup_llm_selection(llm_preset=llm_preset)

    logging.basicConfig(level=logging.WARNING)

    from tabulaflow.app.tui import run_tui

    asyncio.run(
        run_tui(
            llm_selection=startup_llm,
            service_tier=service_tier.value,
            output_pane_host=output_pane_host,
            output_pane_port=output_pane_port,
            output_pane_public_url=output_pane_public_url,
        )
    )
