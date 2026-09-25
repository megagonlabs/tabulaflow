from __future__ import annotations

import json
from pathlib import Path

import pytest

from tabulaflow.app.config import (
    ANTHROPIC_DEFAULT_LLM_CONFIG,
    LLM_OFF,
    OPENAI_DEFAULT_LLM_CONFIG,
    AppConfig,
    InvalidAppConfigError,
    LLMConfig,
    LLMRoleConfig,
    ResolvedLLMConfig,
    fanout_concurrency_for_rpm,
    load_app_config,
    model_supports_apply_patch,
    resolve_llm_config,
    save_app_config,
    update_app_config,
)


def _config() -> LLMConfig:
    return LLMConfig(
        main=LLMRoleConfig(model="together:owner/main", effort="high"),
        subagent=LLMRoleConfig(model="together:owner/fast", effort="low"),
    )


def test_default_config_is_automatic() -> None:
    assert AppConfig().llm is None


def test_openai_defaults_use_gpt_5_6_sol() -> None:
    assert OPENAI_DEFAULT_LLM_CONFIG.main.model == "openai:gpt-5.6-sol"
    assert OPENAI_DEFAULT_LLM_CONFIG.subagent.model == "openai:gpt-5.6-luna"


def test_anthropic_defaults_use_claude_5() -> None:
    assert ANTHROPIC_DEFAULT_LLM_CONFIG.main.model == "anthropic:claude-opus-5-5"
    assert ANTHROPIC_DEFAULT_LLM_CONFIG.subagent.model == "anthropic:claude-sonnet-5"


def test_resolved_config_exposes_effective_request_rate() -> None:
    assert ResolvedLLMConfig(None, None).requests_per_minute == 300
    config = _config().model_copy(update={"requests_per_minute": 1500})
    assert ResolvedLLMConfig(config, config).requests_per_minute == 1500


@pytest.mark.parametrize(
    ("rpm", "expected"),
    [(300, 50), (600, 100), (1500, 250), (3000, 500), (6000, 1000)],
)
def test_fanout_concurrency_tracks_ten_seconds_of_requests(rpm: int, expected: int) -> None:
    assert fanout_concurrency_for_rpm(rpm) == expected


def test_model_identifier_must_be_provider_qualified() -> None:
    with pytest.raises(ValueError, match="provider:model"):
        LLMRoleConfig(model="gpt-5")
    assert LLMRoleConfig(model=" openai:gpt-5 ").model == "openai:gpt-5"


def test_explicit_config_round_trip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    config = AppConfig(llm=_config())
    save_app_config(config, path)
    assert load_app_config(path) == config
    saved = json.loads(Path(path).read_text())
    assert saved["llm"]["main"] == {"model": "together:owner/main", "effort": "high"}


def test_old_reasoning_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="reasoning"):
        AppConfig.model_validate(
            {"llm": {"main": {"model": "test", "reasoning": "high"}, "subagent": {"model": "test"}}}
        )


def test_off_round_trip(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    save_app_config(AppConfig(llm=LLM_OFF), path)
    assert load_app_config(path).llm == LLM_OFF


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    assert load_app_config(str(tmp_path / "missing.json")) == AppConfig()


def test_invalid_or_old_config_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(json.dumps({"llm_preset": "OpenAI balanced"}))
    with pytest.raises(InvalidAppConfigError, match="llm_preset"):
        load_app_config(str(path))


def test_invalid_config_gets_a_concise_validation_error(tmp_path: Path) -> None:
    path = tmp_path / "app_config.json"
    path.write_text(
        json.dumps(
            {
                "llm": {
                    "main": {"model": "openai:gpt-5", "reasoning": "high"},
                    "subagent": {"model": "openai:gpt-5-mini", "reasoning": "medium"},
                }
            }
        )
    )

    with pytest.raises(InvalidAppConfigError) as exc_info:
        load_app_config(str(path))

    assert str(exc_info.value) == (
        f"Invalid app configuration: {path}\n"
        "llm.main.reasoning: Extra inputs are not permitted. Fix or delete the file."
    )


def test_resolve_explicit_and_off() -> None:
    config = _config()
    assert resolve_llm_config(AppConfig(llm=config)) == ResolvedLLMConfig(config, config)
    assert resolve_llm_config(AppConfig(llm=LLM_OFF)) == ResolvedLLMConfig(LLM_OFF, None)


def test_resolve_automatic_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    assert resolve_llm_config(AppConfig()) == ResolvedLLMConfig(None, ANTHROPIC_DEFAULT_LLM_CONFIG, "ANTHROPIC_API_KEY")
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    assert resolve_llm_config(AppConfig()) == ResolvedLLMConfig(None, OPENAI_DEFAULT_LLM_CONFIG, "OPENAI_API_KEY")


def test_resolve_without_credentials_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert resolve_llm_config(AppConfig()) == ResolvedLLMConfig(None, None)


def test_update_app_config(tmp_path: Path) -> None:
    path = str(tmp_path / "app_config.json")
    update_app_config(path, llm=_config())
    assert load_app_config(path).llm == _config()


@pytest.mark.parametrize(
    ("model", "supported"),
    [
        ("openai:gpt-5.6-sol", True),
        ("openai-responses:gpt-5.6-sol", True),
        ("openai:gpt-5", True),
        ("anthropic:claude-opus-5", False),
    ],
)
def test_apply_patch_support(model: str, supported: bool) -> None:
    assert model_supports_apply_patch(model) is supported
