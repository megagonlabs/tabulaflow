"""Persistent app-level configuration for interactive LLM presets.

Distinct from the process-level library config in ``tabulaflow.core.config``:
this holds durable preferences for the interactive app only, persisted at
``~/.tabulaflow/app_config.json``. The config stores an optional selected LLM
preset plus optional user-defined presets. CLI flags are runtime overrides and
are not persisted here.

Example config with an explicitly selected custom preset::

    {
      "active_llm_preset": "My research stack",
      "custom_llm_presets": [
        {
          "label": "My research stack",
          "main": {
            "model": "openai-responses:gpt-5.5",
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
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

APP_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".tabulaflow", "app_config.json")

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


_DEFAULT_LLM_PRESETS_DATA = (
    {
        "label": "OpenAI balanced",
        "main": {
            "model": "openai-responses:gpt-5.5",
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
            "model": "anthropic:claude-opus-4-8",
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
    """The user's durable preferences for the interactive app."""

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=())

    active_llm_preset: str | None = None
    custom_llm_presets: list[LLMPreset] = Field(default_factory=list)

    @property
    def llm_presets(self) -> list[LLMPreset]:
        """Built-in presets with custom entries merged by label.

        A custom preset whose ``label`` matches a built-in replaces that
        built-in in place. New custom labels are appended after the defaults.
        """
        by_label = {preset.label: preset for preset in self.custom_llm_presets}
        merged = [by_label.pop(preset.label, preset) for preset in DEFAULT_LLM_PRESETS]
        return merged + list(by_label.values())

    @property
    def active_preset(self) -> LLMPreset | None:
        """Return the selected preset, or None when no valid preset is selected."""
        if self.active_llm_preset is None:
            return None
        for preset in self.llm_presets:
            if preset.label == self.active_llm_preset:
                return preset
        return None


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
