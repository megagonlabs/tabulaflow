"""Persistent app-level configuration (the user's session preferences).

Distinct from the process-level library config in ``tabulaflow.core.config``:
this holds durable preferences for the interactive app only, persisted at
``~/.tabulaflow/app_config.json``. Resolution order for each option:
built-in default < app_config.json < CLI flag < runtime change.
"""

from __future__ import annotations

import json
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

APP_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".tabulaflow", "app_config.json")

ReasoningEffort = Literal["minimal", "low", "medium", "high"]


class AppConfig(BaseModel):
    """The user's durable preferences for the interactive app."""

    model_config = ConfigDict(validate_assignment=True)

    model: str = "openai-responses:gpt-5.4"
    reasoning_effort: ReasoningEffort = "medium"


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
    """Atomically persist ``config`` to ``path``."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(config.model_dump(), f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
