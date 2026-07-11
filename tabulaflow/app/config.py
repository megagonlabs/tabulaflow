"""Persistent app-level configuration (the user's session preferences).

Distinct from the process-level library config in ``tabulaflow.core.config``:
this holds durable preferences for the interactive app only, persisted at
``~/.tabulaflow/app_config.json``. Resolution order for each option:
built-in default < app_config.json < CLI flag < runtime change.

Only deliberately-set fields are written to the file (``exclude_unset``), so
built-in defaults — notably the model catalog — stay live and evolve with the
code unless the user explicitly overrides them. Example catalog override::

    {
      "model_options": [
        {"model": "openai-responses:gpt-5.4", "label": "GPT-5.4",
         "efforts": ["minimal", "low", "medium", "high"], "default_effort": "medium"},
        {"model": "together:my-org/my-model", "label": "My Model"}
      ]
    }
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

APP_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".tabulaflow", "app_config.json")

ReasoningEffort = Literal["minimal", "low", "medium", "high"]

_ALL_EFFORTS: tuple[ReasoningEffort, ...] = ("minimal", "low", "medium", "high")


class ModelOption(BaseModel):
    """A model offered by the config panel, with its reasoning-effort capabilities."""

    model: str
    """pydantic-ai model identifier, e.g. ``openai-responses:gpt-5.4``."""
    label: str
    """Compact display name, e.g. ``GPT-5.4``."""
    efforts: tuple[ReasoningEffort, ...] = ()
    """Supported reasoning efforts, ordered low to high; empty = not applicable."""
    default_effort: ReasoningEffort | None = None
    """Effort to fall back to when the current one is unsupported by this model."""

    @model_validator(mode="after")
    def _validate_default_effort(self) -> Self:
        if self.efforts:
            if self.default_effort not in self.efforts:
                raise ValueError(f"default_effort {self.default_effort!r} must be one of efforts {self.efforts}")
        elif self.default_effort is not None:
            raise ValueError("default_effort requires a non-empty efforts list")
        return self


DEFAULT_MODEL_OPTIONS: tuple[ModelOption, ...] = (
    ModelOption(model="openai-responses:gpt-5.4", label="GPT-5.4", efforts=_ALL_EFFORTS, default_effort="medium"),
    ModelOption(model="openai-responses:gpt-5", label="GPT-5", efforts=_ALL_EFFORTS, default_effort="medium"),
    ModelOption(model="openai-responses:gpt-5-mini", label="GPT-5 Mini", efforts=_ALL_EFFORTS, default_effort="medium"),
    ModelOption(model="anthropic:claude-sonnet-4-5-20250929", label="Claude Sonnet 4.5"),
    ModelOption(model="google-vertex:gemini-2.5-flash", label="Gemini 2.5 Flash"),
)


class AppConfig(BaseModel):
    """The user's durable preferences for the interactive app."""

    # ``protected_namespaces`` freed up for the ``model_options`` field name.
    model_config = ConfigDict(validate_assignment=True, protected_namespaces=())

    model: str = "openai-responses:gpt-5.4"
    reasoning_effort: ReasoningEffort = "medium"
    # Full replacement when present in the file: the user owns the whole catalog.
    model_options: list[ModelOption] = Field(default_factory=lambda: list(DEFAULT_MODEL_OPTIONS))


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

    ``exclude_unset`` keeps built-in defaults (notably the model catalog) out
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

    Re-reads the file so hand edits (e.g. a custom ``model_options`` catalog)
    survive; only the supplied fields are overwritten.
    """
    config = load_app_config(path)
    for name, value in prefs.items():
        setattr(config, name, value)
    save_app_config(config, path)
