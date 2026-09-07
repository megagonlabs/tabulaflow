"""Human- and LLM-readable output formatting."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.output.formatting._core import (
        format_connector_summary,
        format_dataframe,
        format_exec_result_markdown,
        format_json_schema_type,
        format_single_line_text,
        summarize_binary_values,
    )
    from tabulaflow.output.formatting.cypher import CypherSchemaFormatter
    from tabulaflow.output.formatting.schema import (
        PropertyGraphSchemaFormatter,
        SQLSchemaFormatter,
        schema_formatter_registry,
    )
    from tabulaflow.output.formatting.sql_basic import SQLBasicSchemaFormatter
    from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter

_LAZY_EXPORTS = {
    "CypherSchemaFormatter": ("tabulaflow.output.formatting.cypher", "CypherSchemaFormatter"),
    "PropertyGraphSchemaFormatter": (
        "tabulaflow.output.formatting.schema",
        "PropertyGraphSchemaFormatter",
    ),
    "SQLBasicSchemaFormatter": ("tabulaflow.output.formatting.sql_basic", "SQLBasicSchemaFormatter"),
    "SQLDDLSchemaFormatter": ("tabulaflow.output.formatting.sql_ddl", "SQLDDLSchemaFormatter"),
    "SQLSchemaFormatter": ("tabulaflow.output.formatting.schema", "SQLSchemaFormatter"),
    "format_connector_summary": ("tabulaflow.output.formatting._core", "format_connector_summary"),
    "format_dataframe": ("tabulaflow.output.formatting._core", "format_dataframe"),
    "format_exec_result_markdown": ("tabulaflow.output.formatting._core", "format_exec_result_markdown"),
    "format_json_schema_type": ("tabulaflow.output.formatting._core", "format_json_schema_type"),
    "format_single_line_text": ("tabulaflow.output.formatting._core", "format_single_line_text"),
    "summarize_binary_values": ("tabulaflow.output.formatting._core", "summarize_binary_values"),
    "schema_formatter_registry": ("tabulaflow.output.formatting.schema", "schema_formatter_registry"),
}

__all__ = [
    "CypherSchemaFormatter",
    "PropertyGraphSchemaFormatter",
    "SQLBasicSchemaFormatter",
    "SQLDDLSchemaFormatter",
    "SQLSchemaFormatter",
    "format_connector_summary",
    "format_dataframe",
    "format_exec_result_markdown",
    "format_json_schema_type",
    "format_single_line_text",
    "schema_formatter_registry",
    "summarize_binary_values",
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
