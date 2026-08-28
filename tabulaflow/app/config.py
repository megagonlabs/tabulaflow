"""Persistent app-level configuration for interactive LLM presets.

Distinct from the process-level library config in ``tabulaflow.config``:
this holds durable preferences for the interactive app only, persisted at
``~/.tabulaflow/app_config.json``. The config stores an LLM preset selection
plus optional user-defined presets. CLI flags are runtime overrides and are not
persisted here.

Example config with an explicitly selected custom preset::

    {
      "llm_preset": "My research stack",
      "custom_llm_presets": [
        {
          "label": "My research stack",
          "main": {
            "model": "openai-responses:gpt-5.6-sol",
            "reasoning_effort": "high"
          },
          "subagent": {
            "model": "anthropic:claude-sonnet-4-5-20250929",
            "reasoning_effort": "medium"
          }
        }
      ]
    }
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from tabulaflow._paths import DEFAULT_HOME_DIR

APP_CONFIG_PATH = str(DEFAULT_HOME_DIR / "app_config.json")
LLM_OFF = "off"
LLM_OFF_LABEL = "Off"
PROVIDER_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openai-chat": "OPENAI_API_KEY",
    "openai-responses": "OPENAI_API_KEY",
    "together": "TOGETHER_API_KEY",
}
_INFERRED_PRESET_BY_API_KEY = (
    (PROVIDER_API_KEY_ENV["openai"], "OpenAI balanced"),
    (PROVIDER_API_KEY_ENV["anthropic"], "Anthropic balanced"),
)


def model_supports_apply_patch(model: str) -> bool:
    """Whether the app should expose the GPT-trained patch tool."""
    provider, _, model_name = model.partition(":")
    if provider != "openai-responses":
        return False
    version_match = re.match(r"^gpt-(\d+)(?:[.-]|$)", model_name)
    return version_match is not None and int(version_match.group(1)) >= 5


ReasoningEffort = Literal["low", "medium", "high", "xhigh"]
"""Unified thinking level, translated per provider by pydantic-ai (budget tokens
for older Claude, native effort for newer, ``thinking_level`` for Gemini 3+).
Levels a provider lacks saturate to its nearest supported value."""


class LLMRoleConfig(BaseModel):
    """Model settings for one role in an LLM preset."""

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=())

    model: str
    reasoning_effort: ReasoningEffort = "medium"


class LLMPreset(BaseModel):
    """A named pair of main/subagent LLM settings."""

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=())

    label: str
    main: LLMRoleConfig
    subagent: LLMRoleConfig

    @field_validator("label")
    @classmethod
    def label_is_not_reserved(cls, label: str) -> str:
        """Reject the label reserved for disabling the LLM."""
        label = label.strip()
        if not label:
            raise ValueError("LLM preset labels cannot be empty")
        if label.casefold() == LLM_OFF:
            raise ValueError(f"{label!r} is reserved for LLM preset selection")
        return label


_DEFAULT_LLM_PRESETS_DATA = (
    {
        "label": "OpenAI balanced",
        "main": {
            "model": "openai-responses:gpt-5.6-sol",
            "reasoning_effort": "medium",
        },
        "subagent": {
            "model": "openai-responses:gpt-5.4-mini",
            "reasoning_effort": "medium",
        },
    },
    {
        "label": "OpenAI budget",
        "main": {
            "model": "openai-responses:gpt-5.4-mini",
            "reasoning_effort": "medium",
        },
        "subagent": {
            "model": "openai-responses:gpt-5-mini",
            "reasoning_effort": "medium",
        },
    },
    {
        "label": "Anthropic balanced",
        "main": {
            "model": "anthropic:claude-opus-5",
            "reasoning_effort": "high",
        },
        "subagent": {
            "model": "anthropic:claude-sonnet-4-5-20250929",
            "reasoning_effort": "medium",
        },
    },
    {
        "label": "Planning hybrid",
        "main": {
            "model": "anthropic:claude-opus-4-8",
            "reasoning_effort": "high",
        },
        "subagent": {
            "model": "openai-responses:gpt-5.4-mini",
            "reasoning_effort": "medium",
        },
    },
)
DEFAULT_LLM_PRESETS: tuple[LLMPreset, ...] = tuple(
    LLMPreset.model_validate(preset) for preset in _DEFAULT_LLM_PRESETS_DATA
)


class AppConfig(BaseModel):
    """The user's durable preferences for the interactive app.

    ``llm_preset=None`` means the user has no explicit preference, so startup
    infers a preset from available credentials. ``off`` and preset labels are
    explicit, persistent choices.
    """

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=(), extra="forbid")

    llm_preset: str | None = None
    custom_llm_presets: list[LLMPreset] = Field(default_factory=list)

    @field_validator("llm_preset")
    @classmethod
    def normalize_llm_preset(cls, selection: str | None) -> str | None:
        """Normalize explicit Off while preserving preset label casing."""
        if selection is None:
            return None
        selection = selection.strip()
        if not selection:
            raise ValueError("LLM preset selection cannot be empty")
        return LLM_OFF if selection.casefold() == LLM_OFF else selection

    @model_validator(mode="after")
    def selected_preset_exists(self) -> AppConfig:
        """Reject named selections that do not exist in the preset catalog."""
        selection = self.llm_preset
        if selection is not None and selection != LLM_OFF and self.preset_by_label(selection) is None:
            raise ValueError(f"Unknown LLM preset: {selection}")
        return self

    @property
    def llm_presets(self) -> list[LLMPreset]:
        """Built-in presets with custom entries merged by label.

        A custom preset whose ``label`` matches a built-in replaces that
        built-in in place. New custom labels are appended after the defaults.
        """
        by_label = {preset.label: preset for preset in self.custom_llm_presets}
        merged = [by_label.pop(preset.label, preset) for preset in DEFAULT_LLM_PRESETS]
        return merged + list(by_label.values())

    def preset_by_label(self, label: str) -> LLMPreset | None:
        """Return the preset named ``label``, or None if it is absent."""
        for preset in self.llm_presets:
            if preset.label == label:
                return preset
        return None


@dataclass(frozen=True)
class ResolvedLLMSelection:
    """User LLM intent paired atomically with its effective runtime preset."""

    selection: str | None
    preset: LLMPreset | None
    # Environment-variable name that caused inference (for example,
    # OPENAI_API_KEY), never the secret value. None for explicit selections.
    detected_api_key_env: str | None = None

    def __post_init__(self) -> None:
        """Reject combinations that cannot result from selection resolution."""
        if self.selection is not None and not self.selection.strip():
            raise ValueError("LLM selection cannot be empty")
        if self.selection == LLM_OFF and self.preset is not None:
            raise ValueError("LLM off cannot resolve to a preset")
        if self.selection not in {None, LLM_OFF} and self.preset is None:
            raise ValueError("A named LLM selection must resolve to a preset")
        if self.selection not in {None, LLM_OFF} and self.preset is not None and self.selection != self.preset.label:
            raise ValueError("A named LLM selection must match its preset label")
        if self.detected_api_key_env is not None and (self.selection is not None or self.preset is None):
            raise ValueError("Detected credentials are only valid for an inferred preset")


def _normalize_llm_selection(selection: str) -> str:
    selection = selection.strip()
    return LLM_OFF if selection.casefold() == LLM_OFF else selection


def resolve_llm_selection(config: AppConfig, *, override: str | None = None) -> ResolvedLLMSelection:
    """Resolve persisted or launch-specific LLM intent into a runtime preset.

    Args:
        config: Loaded app config.
        override: Optional ``off`` or preset label for this launch.

    Returns:
        The selection and its effective preset. A ``None`` selection means the
        user has no explicit preference, so credentials determine the preset.
        The preset is ``None`` when no supported credentials are available or
        when the selection is ``off``.

    Raises:
        ValueError: If the selection is empty or names no known preset.
    """
    selection = config.llm_preset if override is None else _normalize_llm_selection(override)
    if selection == "":
        raise ValueError("LLM preset selection cannot be empty")
    if selection == LLM_OFF:
        return ResolvedLLMSelection(selection=selection, preset=None)
    if selection is None:
        for variable, label in _INFERRED_PRESET_BY_API_KEY:
            if os.getenv(variable, "").strip():
                return ResolvedLLMSelection(
                    selection=None,
                    preset=config.preset_by_label(label),
                    detected_api_key_env=variable,
                )
        return ResolvedLLMSelection(selection=selection, preset=None)

    preset = config.preset_by_label(selection)
    if preset is None:
        raise ValueError(f"Unknown LLM preset: {selection}")
    return ResolvedLLMSelection(selection=selection, preset=preset)


def load_app_config(path: str = APP_CONFIG_PATH) -> AppConfig:
    """Load the app config from ``path``, returning defaults if the file is absent.

    Raises:
        ValueError: If the file exists but is not valid app-config JSON.
    """
    if not os.path.exists(path):
        return AppConfig()
    try:
        with open(path) as f:
            data = json.load(f)
        return AppConfig.model_validate(data)
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        raise ValueError(f"Invalid app config at {path}: {e}\nFix or delete the file.") from e


def save_app_config(config: AppConfig, path: str = APP_CONFIG_PATH) -> None:
    """Atomically persist ``config``'s deliberately-set fields to ``path``.

    ``exclude_unset`` keeps built-in defaults out of the file, so they stay live
    across app updates.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(config.model_dump(mode="json", exclude_unset=True), f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def update_app_config(path: str = APP_CONFIG_PATH, **prefs: Any) -> None:
    """Load-modify-save ``prefs`` onto the persisted config.

    Re-reads the file so hand edits, especially ``custom_llm_presets``, survive;
    only the supplied fields are overwritten.
    """
    config = load_app_config(path)
    data = config.model_dump(mode="python")
    data.update(prefs)
    save_app_config(AppConfig.model_validate(data), path)
