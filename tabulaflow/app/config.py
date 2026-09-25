"""Persistent LLM configuration for the interactive application."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from tabulaflow._paths import DEFAULT_HOME_DIR
from tabulaflow.agents.llm import ReasoningLevel, uses_openai_responses

APP_CONFIG_PATH = str(DEFAULT_HOME_DIR / "app_config.json")
LLM_OFF: Literal["off"] = "off"
LLMRequestsPerMinute: TypeAlias = Literal[300, 600, 1500, 3000, 6000]
LLM_REQUEST_RATE_OPTIONS: tuple[LLMRequestsPerMinute, ...] = (300, 600, 1500, 3000, 6000)
APP_MAX_LLM_CONCURRENCY = 1200
APP_MAX_FANOUT_CONCURRENCY = 1000


class InvalidAppConfigError(ValueError):
    """An app configuration file could not be parsed or validated."""


def model_supports_apply_patch(model: str) -> bool:
    """Whether the app should expose the GPT-trained patch tool."""
    _, _, model_name = model.partition(":")
    if not uses_openai_responses(model):
        return False
    version_match = re.match(r"^gpt-(\d+)(?:[.-]|$)", model_name)
    return version_match is not None and int(version_match.group(1)) >= 5


class LLMRoleConfig(BaseModel):
    """Model settings for one agent role."""

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=(), extra="forbid")

    model: str
    effort: ReasoningLevel = "medium"

    @field_validator("model")
    @classmethod
    def model_is_qualified(cls, model: str) -> str:
        """Require a provider-qualified model identifier."""
        model = model.strip()
        if model == "test":
            return model
        provider, separator, name = model.partition(":")
        if not separator or not provider or not name:
            raise ValueError("Model must use the provider:model format")
        return model


class LLMConfig(BaseModel):
    """Atomic model and request-rate configuration for app agents."""

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=(), extra="forbid")

    main: LLMRoleConfig
    subagent: LLMRoleConfig
    requests_per_minute: LLMRequestsPerMinute = 300


def fanout_concurrency_for_rpm(requests_per_minute: int) -> int:
    """Size app fan-out for ten seconds of request starts."""
    return min(APP_MAX_FANOUT_CONCURRENCY, (requests_per_minute + 5) // 6)


OPENAI_DEFAULT_LLM_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="openai:gpt-5.6-sol", effort="medium"),
    subagent=LLMRoleConfig(model="openai:gpt-5.6-luna", effort="medium"),
)
ANTHROPIC_DEFAULT_LLM_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="anthropic:claude-opus-5-5", effort="high"),
    subagent=LLMRoleConfig(model="anthropic:claude-sonnet-5", effort="medium"),
)

RECOMMENDED_MAIN_MODELS: tuple[str, ...] = (
    "openai:gpt-5.6-sol",
)
RECOMMENDED_SUBAGENT_MODELS: tuple[str, ...] = (
    "openai:gpt-6-sol",
    "openai:gpt-5.6-luna",
)


class AppConfig(BaseModel):
    """Durable interactive-app preferences.

    ``None`` chooses defaults from detected credentials, ``"off"`` explicitly
    disables the LLM, and an :class:`LLMConfig` is an explicit configuration.
    """

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=(), extra="forbid")

    llm: LLMConfig | Literal["off"] | None = None


@dataclass(frozen=True)
class ResolvedLLMConfig:
    """Persisted LLM intent paired with its effective runtime configuration."""

    selection: LLMConfig | Literal["off"] | None
    config: LLMConfig | None
    detected_api_key_env: str | None = None

    @property
    def requests_per_minute(self) -> LLMRequestsPerMinute:
        """Return the active request rate, including the app default."""
        return self.config.requests_per_minute if self.config is not None else 300

    def __post_init__(self) -> None:
        if self.selection is not None and self.selection != LLM_OFF and not isinstance(self.selection, LLMConfig):
            raise ValueError("LLM selection must be automatic, off, or an LLM configuration")
        if self.selection == LLM_OFF and self.config is not None:
            raise ValueError("LLM off cannot resolve to a configuration")
        if isinstance(self.selection, LLMConfig) and self.selection != self.config:
            raise ValueError("An explicit LLM selection must be its effective configuration")
        if self.detected_api_key_env is not None and (self.selection is not None or self.config is None):
            raise ValueError("Detected credentials are only valid for automatic configuration")


def resolve_llm_config(config: AppConfig) -> ResolvedLLMConfig:
    """Resolve persisted intent into the effective runtime configuration."""
    if config.llm == LLM_OFF:
        return ResolvedLLMConfig(selection=LLM_OFF, config=None)
    if isinstance(config.llm, LLMConfig):
        return ResolvedLLMConfig(selection=config.llm, config=config.llm)
    if os.getenv("OPENAI_API_KEY", "").strip():
        return ResolvedLLMConfig(None, OPENAI_DEFAULT_LLM_CONFIG, "OPENAI_API_KEY")
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return ResolvedLLMConfig(None, ANTHROPIC_DEFAULT_LLM_CONFIG, "ANTHROPIC_API_KEY")
    return ResolvedLLMConfig(selection=None, config=None)


def load_app_config(path: str = APP_CONFIG_PATH) -> AppConfig:
    """Load app configuration, returning defaults when the file is absent."""
    if not os.path.exists(path):
        return AppConfig()
    try:
        with open(path) as f:
            return AppConfig.model_validate(json.load(f))
    except json.JSONDecodeError as error:
        detail = f"Invalid JSON at line {error.lineno}, column {error.colno}."
        raise InvalidAppConfigError(_invalid_app_config_message(path, detail)) from error
    except ValidationError as error:
        errors = error.errors(include_url=False, include_context=False, include_input=False)
        relevant = [item for item in errors if "literal['off']" not in item["loc"]]
        item = (relevant or errors)[0]
        location = ".".join(str(part) for part in item["loc"] if part != "LLMConfig")
        detail = f"{location}: {item['msg']}."
        raise InvalidAppConfigError(_invalid_app_config_message(path, detail)) from error


def _invalid_app_config_message(path: str, detail: str) -> str:
    display_path = path.replace(os.path.expanduser("~"), "~", 1)
    return f"Invalid app configuration: {display_path}\n{detail} Fix or delete the file."


def save_app_config(config: AppConfig, path: str = APP_CONFIG_PATH) -> None:
    """Atomically persist deliberately set app configuration fields."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(config.model_dump(mode="json", exclude_unset=True), f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def update_app_config(path: str = APP_CONFIG_PATH, **prefs: Any) -> None:
    """Load, update, validate, and save app preferences."""
    config = load_app_config(path)
    data = config.model_dump(mode="python")
    data.update(prefs)
    save_app_config(AppConfig.model_validate(data), path)
