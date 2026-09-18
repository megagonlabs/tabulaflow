"""Persistent LLM configuration for the interactive application."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from tabulaflow._paths import DEFAULT_HOME_DIR
from tabulaflow.agents.llm import ReasoningLevel, uses_openai_responses

APP_CONFIG_PATH = str(DEFAULT_HOME_DIR / "app_config.json")
LLM_OFF: Literal["off"] = "off"


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
    """Atomic model configuration for the main agent and subagent."""

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=(), extra="forbid")

    main: LLMRoleConfig
    subagent: LLMRoleConfig


OPENAI_DEFAULT_LLM_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="openai:gpt-5.6-sol", effort="medium"),
    subagent=LLMRoleConfig(model="openai:gpt-5.4-mini", effort="medium"),
)
ANTHROPIC_DEFAULT_LLM_CONFIG = LLMConfig(
    main=LLMRoleConfig(model="anthropic:claude-opus-5", effort="high"),
    subagent=LLMRoleConfig(model="anthropic:claude-sonnet-4-5-20250929", effort="medium"),
)

RECOMMENDED_MAIN_MODELS: tuple[str, ...] = (
    "openai:gpt-5.6-sol",
    "openai:gpt-5.6-terra",
)
RECOMMENDED_SUBAGENT_MODELS: tuple[str, ...] = (
    "openai:gpt-5.4-mini",
    "openai:gpt-5-mini",
)
_CURATED_MODELS_BY_PROVIDER = (
    (
        "openai",
        (
            "gpt-6-astra",
            "gpt-5.6-sol",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "gpt-5.5",
            "gpt-5",
            "gpt-5.4-mini",
            "gpt-5-mini",
        ),
    ),
    (
        "anthropic",
        (
            "claude-opus-5",
            "claude-sonnet-5",
            "claude-haiku-4-5",
            "claude-fable-5-1",
        ),
    ),
    (
        "google",
        (
            "gemini-3.8-flash",
            "gemini-3.1-pro-preview",
        ),
    ),
    (
        "google-cloud",
        (
            "gemini-3.8-flash",
            "gemini-3.1-pro-preview",
        ),
    ),
    (
        "xai",
        (
            "grok-4.6",
        ),
    ),
    (
        "moonshotai",
        ("kimi-k3",),
    ),
    ("deepseek", ("deepseek-v4-pro", "deepseek-v4-flash")),
    (
        "zai",
        ("glm-5.3",),
    ),
    (
        "bedrock",
        (
            "global.anthropic.claude-opus-5",
            "global.anthropic.claude-opus-4-8",
            "global.anthropic.claude-sonnet-5",
            "us.anthropic.claude-sonnet-4-6",
            "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "global.anthropic.claude-fable-5-1",
            "global.anthropic.claude-fable-5",
            "global.openai.gpt-5.6-sol",
            "global.openai.gpt-5.6-terra",
            "global.openai.gpt-5.6-luna",
            "us.meta.llama4-maverick-17b-instruct-v1:0",
            "us.meta.llama4-scout-17b-instruct-v1:0",
            "global.amazon.nova-2-lite-v1:0",
            "us.amazon.nova-premier-v1:0",
            "deepseek.r1-v1:0",
            "deepseek.v3.2",
            "moonshotai.kimi-k2.5",
            "moonshot.kimi-k2-thinking",
            "minimax.minimax-m2.5",
            "minimax.minimax-m2.1",
            "mistral.mistral-large-3-675b-instruct",
            "mistral.devstral-2-123b",
            "nvidia.nemotron-nano-3-30b",
            "nvidia.nemotron-super-3-120b",
            "qwen.qwen3-next-80b-a3b",
            "qwen.qwen3-coder-next",
            "qwen.qwen3-vl-235b-a22b",
            "zai.glm-5",
            "zai.glm-4.7",
        ),
    ),
    (
        "bedrock-mantle",
        (
            "openai.gpt-5.6-sol",
            "openai.gpt-5.6-terra",
            "openai.gpt-5.6-luna",
            "openai.gpt-5.5",
            "openai.gpt-oss-120b",
            "openai.gpt-oss-20b",
        ),
    ),
    (
        "groq",
        (
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ),
    ),
    ("mistral", ("mistral-large-latest", "mistral-small-latest", "codestral-latest")),
    ("cerebras", ("zai-glm-4.7", "gemma-4-31b", "gpt-oss-120b")),
    ("cohere", ("command-nightly", "command-r-plus-08-2024", "command-r-08-2024", "command-r7b-12-2024")),
    (
        "huggingface",
        (
            "Qwen/Qwen3-235B-A22B",
            "Qwen/Qwen3-32B",
            "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "deepseek-ai/DeepSeek-R1",
        ),
    ),
    (
        "snowflake",
        (
            "claude-opus-5",
            "claude-opus-4-8",
            "claude-sonnet-5",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
            "openai-gpt-5-6-sol",
            "openai-gpt-5-6-terra",
            "openai-gpt-5-6-luna",
            "openai-gpt-5.5",
            "openai-gpt-5.4",
            "llama4-maverick",
            "snowflake-llama-3.3-70b",
            "deepseek-r1",
            "mistral-large2",
        ),
    ),
    (
        "heroku",
        (
            "claude-opus-4-6",
            "claude-opus-4-5",
            "claude-4-6-sonnet",
            "claude-4-5-sonnet",
            "claude-4-5-haiku",
            "deepseek-v3-2",
            "glm-4-7",
            "glm-4-7-flash",
            "kimi-k2-5",
            "kimi-k2-thinking",
            "minimax-m2-1",
            "minimax-m2",
            "nova-2-lite",
            "qwen3-235b",
            "qwen3-coder-480b",
            "gpt-oss-120b",
        ),
    ),
    (
        "crusoe",
        (
            "deepseek-ai/DeepSeek-V4-Pro",
            "deepseek-ai/Deepseek-V4-Flash",
            "zai/GLM-5.2",
            "zai/GLM-5.1",
            "moonshotai/Kimi-K2.6",
            "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "meta-llama/Llama-3.3-70B-Instruct",
            "google/gemma-4-31b-it",
            "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B",
            "nvidia/Nemotron-3.5-Lightning-30B-A3B",
            "openai/gpt-oss-120b",
        ),
    ),
    ("typesafe", ("jev-latest", "jev-preview")),
)
CURATED_MODEL_CATALOG = tuple(
    f"{provider}:{model}" for provider, models in _CURATED_MODELS_BY_PROVIDER for model in models
)


def llm_model_catalog(*, current: str, recommended: tuple[str, ...]) -> tuple[str, ...]:
    """Return recommendations, the current model, and the curated model catalog."""
    current_provider = current.partition(":")[0]
    current_provider_models = tuple(
        model for model in CURATED_MODEL_CATALOG if model.partition(":")[0] == current_provider
    )
    other_models = tuple(model for model in CURATED_MODEL_CATALOG if model.partition(":")[0] != current_provider)
    models = (*recommended, current, *current_provider_models, *other_models)
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
