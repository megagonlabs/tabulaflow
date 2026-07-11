"""Persistent app-level configuration (the user's session preferences).

Distinct from the process-level library config in ``tabulaflow.core.config``:
this holds durable preferences for the interactive app only, persisted at
``~/.tabulaflow/app_config.json``. Resolution order for each option:
built-in default < app_config.json < CLI flag < runtime change.

Only deliberately-set fields are written to the file (``exclude_unset``), so
built-in defaults — notably the model catalog — stay live and evolve with the
code unless the user explicitly overrides them. Example catalog override::

    {
      "custom_model_options": [
        {"model": "together:my-org/my-model", "label": "My Model"}
      ],
      "custom_subagent_model_options": [
        {"model": "together:my-org/my-fast-model", "label": "My Fast Model"}
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


class ModelOption(BaseModel):
    """A model offered by the config panel — pure display data.

    Thinking capabilities are read from the live model's pydantic-ai profile,
    not declared here.
    """

    model: str
    """pydantic-ai model identifier, e.g. ``openai-responses:gpt-5.5``."""
    label: str
    """Compact display name, e.g. ``GPT-5.5``."""
    recommended_effort: ReasoningEffort | None = None
    """Vendor-tool default effort for this model (e.g. Codex ships GPT at
    ``medium``, Claude Code ships Claude at ``high``). Applied when the model
    is selected in the config screen; ``None`` = no sourced recommendation,
    the current effort carries over."""


DEFAULT_MODEL_OPTIONS: tuple[ModelOption, ...] = (
    ModelOption(model="openai-responses:gpt-5.5", label="GPT-5.5", recommended_effort="medium"),
    ModelOption(model="openai-responses:gpt-5.4-mini", label="GPT-5.4 Mini", recommended_effort="medium"),
    ModelOption(model="anthropic:claude-opus-4-8", label="Claude Opus 4.8", recommended_effort="high"),
    ModelOption(model="google-vertex:gemini-3.1-pro-preview", label="Gemini 3.1 Pro"),
)

DEFAULT_SUBAGENT_MODEL_OPTIONS: tuple[ModelOption, ...] = (
    ModelOption(model="openai-responses:gpt-5.4-mini", label="GPT-5.4 Mini", recommended_effort="medium"),
    ModelOption(model="anthropic:claude-sonnet-4-5-20250929", label="Claude Sonnet 4.5", recommended_effort="medium"),
)


class AppConfig(BaseModel):
    """The user's durable preferences for the interactive app."""

    # ``protected_namespaces`` freed up for the ``custom_*_model_options`` field names.
    model_config = ConfigDict(validate_assignment=True, protected_namespaces=())

    model: str = "openai-responses:gpt-5.5"
    reasoning_effort: ReasoningEffort = "medium"
    subagent_model: str = "openai-responses:gpt-5.4-mini"
    subagent_reasoning_effort: ReasoningEffort = "medium"
    # Appended to the built-in defaults rather than replacing them, so catalog
    # updates in future versions still reach users with custom entries. A custom
    # entry whose ``model`` matches a default overrides that default in place.
    custom_model_options: list[ModelOption] = Field(default_factory=list)
    custom_subagent_model_options: list[ModelOption] = Field(default_factory=list)

    @property
    def model_options(self) -> list[ModelOption]:
        """Main-agent catalog: built-in defaults with custom entries merged in."""
        by_id = {option.model: option for option in self.custom_model_options}
        merged = [by_id.pop(option.model, option) for option in DEFAULT_MODEL_OPTIONS]
        return merged + list(by_id.values())

    @property
    def subagent_model_options(self) -> list[ModelOption]:
        """Subagent catalog: built-in defaults with custom entries merged in."""
        by_id = {option.model: option for option in self.custom_subagent_model_options}
        merged = [by_id.pop(option.model, option) for option in DEFAULT_SUBAGENT_MODEL_OPTIONS]
        return merged + list(by_id.values())


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
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Invalid app config at {path}: {e}\nFix or delete the file.") from e


def save_app_config(config: AppConfig, path: str = APP_CONFIG_PATH) -> None:
    """Atomically persist ``config``'s deliberately-set fields to ``path``.

    ``exclude_unset`` keeps built-in defaults (notably the model catalogs) out
    of the file, so they stay live across app updates.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(config.model_dump(mode="json", exclude_unset=True), f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def update_app_config(path: str = APP_CONFIG_PATH, **prefs: Any) -> None:
    """Load-modify-save ``prefs`` onto the persisted config.

    Re-reads the file so hand edits (e.g. ``custom_model_options`` entries)
    survive; only the supplied fields are overwritten.
    """
    config = load_app_config(path)
    for name, value in prefs.items():
        setattr(config, name, value)
    save_app_config(config, path)
