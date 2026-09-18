"""Persistent LLM configuration for the interactive application."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_ai.models import known_model_names

from tabulaflow._paths import DEFAULT_HOME_DIR
from tabulaflow.agents.llm import ReasoningLevel, uses_openai_responses

APP_CONFIG_PATH = str(DEFAULT_HOME_DIR / "app_config.json")
LLM_OFF: Literal["off"] = "off"


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
    reasoning: ReasoningLevel = "medium"

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
    """Atomic model configuration for the main agent and subagent."""

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=(), extra="forbid")

    main: LLMRoleConfig
    subagent: LLMRoleConfig


OPENAI_DEFAULT_LLM_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="openai:gpt-5.6-sol", reasoning="medium"),
    subagent=LLMRoleConfig(model="openai:gpt-5.4-mini", reasoning="medium"),
)
ANTHROPIC_DEFAULT_LLM_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="anthropic:claude-opus-5", reasoning="high"),
    subagent=LLMRoleConfig(model="anthropic:claude-sonnet-4-5-20250929", reasoning="medium"),
)

RECOMMENDED_MAIN_MODELS: tuple[str, ...] = (
    "openai:gpt-5.6-sol",
    "openai:gpt-5.6-terra",
)
RECOMMENDED_SUBAGENT_MODELS: tuple[str, ...] = (
    "openai:gpt-5.4-mini",
    "openai:gpt-5-mini",
)


def llm_model_catalog(*, current: str, recommended: tuple[str, ...]) -> tuple[str, ...]:
    """Return recommendations, the current model, and every Pydantic AI model id."""
    models = (*recommended, current, *(model for model in known_model_names() if model != "test"))
    return tuple(dict.fromkeys(models))


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
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        raise ValueError(f"Invalid app config at {path}: {e}\nFix or delete the file.") from e


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
