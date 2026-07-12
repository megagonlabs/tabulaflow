"""Entry point for the tabulaflow CLI."""

from typing import get_args

import typer

from tabulaflow.app.config import LLMRoleConfig, ReasoningEffort

app = typer.Typer(
    name="tabulaflow",
    help="Minimalist Text-to-Query toolkit — interactive SQL / Cypher chat.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _validate_model(model: str, *, param_hint: str) -> None:
    from tabulaflow.core.llm import validate_model_identifier

    try:
        validate_model_identifier(model)
    except Exception as exc:
        raise typer.BadParameter(
            f"{model!r} is not a usable LLM model: {exc}",
            param_hint=param_hint,
        ) from None


def _with_role_overrides(
    role: LLMRoleConfig,
    *,
    model: str | None,
    model_param_hint: str,
    reasoning_effort: str | None,
    reasoning_effort_param_hint: str,
    saved_param_hint: str,
) -> LLMRoleConfig:
    data = role.model_dump()
    if model is not None:
        data["model"] = model
    if reasoning_effort is not None:
        data["reasoning_effort"] = reasoning_effort
    try:
        resolved = LLMRoleConfig.model_validate(data)
    except ValueError:
        raise typer.BadParameter(
            f"{reasoning_effort!r} is not one of: {', '.join(get_args(ReasoningEffort))}",
            param_hint=reasoning_effort_param_hint,
        ) from None
    _validate_model(resolved.model, param_hint=model_param_hint if model is not None else saved_param_hint)
    return resolved


def _resolve_llm_roles(
    *,
    model: str | None,
    reasoning_effort: str | None,
    subagent_model: str | None,
    subagent_reasoning_effort: str | None,
) -> tuple[LLMRoleConfig, LLMRoleConfig]:
    from tabulaflow.app.config import load_app_config

    preset = load_app_config().active_preset
    return (
        _with_role_overrides(
            preset.main,
            model=model,
            model_param_hint="--model",
            reasoning_effort=reasoning_effort,
            reasoning_effort_param_hint="--reasoning-effort",
            saved_param_hint="active LLM preset main model",
        ),
        _with_role_overrides(
            preset.subagent,
            model=subagent_model,
            model_param_hint="--subagent-model",
            reasoning_effort=subagent_reasoning_effort,
            reasoning_effort_param_hint="--subagent-reasoning-effort",
            saved_param_hint="active LLM preset subagent model",
        ),
    )


@app.command()
def chat(
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM identifier (e.g. openai-responses:gpt-5.5). Overrides the saved default for this launch.",
    ),
    reasoning_effort: str | None = typer.Option(
        None,
        "--reasoning-effort",
        "-r",
        help="Reasoning effort: low | medium | high | xhigh. Overrides the saved default for this launch.",
    ),
    subagent_model: str | None = typer.Option(
        None,
        "--subagent-model",
        help="LLM identifier for internal fan-out/extraction subagents. Overrides the saved default for this launch.",
    ),
    subagent_reasoning_effort: str | None = typer.Option(
        None,
        "--subagent-reasoning-effort",
        help="Subagent reasoning effort: low | medium | high | xhigh. Overrides the saved default for this launch.",
    ),
    output_pane_port: int | None = typer.Option(
        None,
        "--output-pane-port",
        help="Strict port for the browser output pane. Defaults to the first free port in 61111-61130.",
    ),
    output_pane_host: str = typer.Option(
        "127.0.0.1",
        "--output-pane-host",
        help="Bind host for the browser output pane.",
    ),
    output_pane_public_url: str | None = typer.Option(
        None,
        "--output-pane-public-url",
        help="Browser-facing base URL for the output pane. The session token is appended automatically.",
    ),
) -> None:
    """Start an interactive database chat session (SQL or Neo4j Cypher)."""
    import asyncio

    import tabulaflow

    main, subagent = _resolve_llm_roles(
        model=model,
        reasoning_effort=reasoning_effort,
        subagent_model=subagent_model,
        subagent_reasoning_effort=subagent_reasoning_effort,
    )

    tabulaflow.configure(
        column_stats_mode="always_skip",
        query_cache_enabled=False,
        instrument_enabled=False,
        log_level="WARNING",
    )

    from tabulaflow.app.tui import run_tui

    asyncio.run(
        run_tui(
            model=main.model,
            reasoning_effort=main.reasoning_effort,
            subagent_model=subagent.model,
            subagent_reasoning_effort=subagent.reasoning_effort,
            output_pane_host=output_pane_host,
            output_pane_port=output_pane_port,
            output_pane_public_url=output_pane_public_url,
        )
    )


def main() -> None:
    app()
