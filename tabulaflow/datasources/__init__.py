"""Data source loaders that produce SQLConnector instances."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.datasources.files import DATA_FILE_EXTENSIONS, load_files
    from tabulaflow.datasources.huggingface import (
        is_hf_dataset_url,
        load_hf_dataset,
        parse_hf_dataset_url,
    )

_LAZY_EXPORTS = {
    "DATA_FILE_EXTENSIONS": ("tabulaflow.datasources.files", "DATA_FILE_EXTENSIONS"),
    "load_files": ("tabulaflow.datasources.files", "load_files"),
    "is_hf_dataset_url": ("tabulaflow.datasources.huggingface", "is_hf_dataset_url"),
    "load_hf_dataset": ("tabulaflow.datasources.huggingface", "load_hf_dataset"),
    "parse_hf_dataset_url": ("tabulaflow.datasources.huggingface", "parse_hf_dataset_url"),
}

__all__ = [
    "DATA_FILE_EXTENSIONS",
    "is_hf_dataset_url",
    "load_files",
    "load_hf_dataset",
    "parse_hf_dataset_url",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})
