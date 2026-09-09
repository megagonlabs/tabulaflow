"""Data source loaders that produce SQLConnector instances."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.data.loaders.files import DATA_FILE_EXTENSIONS, load_files
    from tabulaflow.data.loaders.huggingface import (
        HuggingFaceSubsetRequiredError,
        build_hf_dataset_url,
        is_hf_dataset_url,
        load_hf_dataset,
        parse_hf_dataset_url,
    )

_LAZY_EXPORTS = {
    "DATA_FILE_EXTENSIONS": ("tabulaflow.data.loaders.files", "DATA_FILE_EXTENSIONS"),
    "load_files": ("tabulaflow.data.loaders.files", "load_files"),
    "HuggingFaceSubsetRequiredError": (
        "tabulaflow.data.loaders.huggingface",
        "HuggingFaceSubsetRequiredError",
    ),
    "build_hf_dataset_url": ("tabulaflow.data.loaders.huggingface", "build_hf_dataset_url"),
    "is_hf_dataset_url": ("tabulaflow.data.loaders.huggingface", "is_hf_dataset_url"),
    "load_hf_dataset": ("tabulaflow.data.loaders.huggingface", "load_hf_dataset"),
    "parse_hf_dataset_url": ("tabulaflow.data.loaders.huggingface", "parse_hf_dataset_url"),
}

__all__ = [
    "DATA_FILE_EXTENSIONS",
    "HuggingFaceSubsetRequiredError",
    "build_hf_dataset_url",
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
