"""Structured extraction from document text."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.extraction.entity import EntityExtractor

_LAZY_EXPORTS = {
    "EntityExtractor": ("tabulaflow.agents.extraction.entity", "EntityExtractor"),
}

__all__ = ["EntityExtractor"]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})
