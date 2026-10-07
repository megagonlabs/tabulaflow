"""Agent configuration validation shared by research entry points."""

from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel


def resolve_agent_config(agent_cls: type[Any], values: Mapping[str, Any]) -> BaseModel:
    """Build a registered agent's configuration from validated field overrides."""
    config_cls = agent_cls.config_cls
    unknown = sorted(set(values) - set(config_cls.model_fields))
    if unknown:
        available = ", ".join(sorted(config_cls.model_fields))
        raise ValueError(
            f"unknown configuration option for {agent_cls.name}: {', '.join(unknown)}. Available options: {available}"
        )
    return cast(BaseModel, config_cls.model_validate(dict(values)))
