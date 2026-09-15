"""Select formatter classes by schema kind."""

from typing import Literal, overload

from tabulaflow.core import SchemaKind
from tabulaflow.output.formatting import sql_compact  # noqa: F401 -- register the alternative SQL formatter
from tabulaflow.output.formatting.cypher import CypherSchemaFormatter
from tabulaflow.output.formatting.schema import (
    PropertyGraphSchemaFormatter,
    RDFSchemaFormatter,
    SQLSchemaFormatter,
    schema_formatter_registry,
)
from tabulaflow.output.formatting.sparql import SPARQLSchemaFormatter
from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter

_DEFAULT_FORMATTERS: dict[SchemaKind, str] = {
    "sql": SQLDDLSchemaFormatter.name,
    "property_graph": CypherSchemaFormatter.name,
    "rdf": SPARQLSchemaFormatter.name,
}


@overload
def get_schema_formatter_class(kind: Literal["sql"], name: str | None = None) -> type[SQLSchemaFormatter]: ...


@overload
def get_schema_formatter_class(
    kind: Literal["property_graph"], name: str | None = None
) -> type[PropertyGraphSchemaFormatter]: ...


@overload
def get_schema_formatter_class(kind: Literal["rdf"], name: str | None = None) -> type[RDFSchemaFormatter]: ...


def get_schema_formatter_class(
    kind: SchemaKind, name: str | None = None
) -> type[SQLSchemaFormatter | PropertyGraphSchemaFormatter | RDFSchemaFormatter]:
    """Select and validate a formatter class without constructing it.

    Args:
        kind: The schema's discriminator value.
        name: Registered formatter name, or None for the kind's default:
            SQL DDL, Cypher, or SPARQL.

    Returns:
        A compatible formatter class.

    Raises:
        ValueError: The kind or name is unknown, or the formatter is incompatible.
    """
    if kind not in _DEFAULT_FORMATTERS:
        raise ValueError(f"Unknown schema kind: {kind!r}")

    formatter_cls = schema_formatter_registry.get_class(_DEFAULT_FORMATTERS[kind] if name is None else name)
    if formatter_cls.schema_kind != kind:
        raise ValueError(f"Formatter {formatter_cls.name!r} supports {formatter_cls.schema_kind!r}, not {kind!r}")
    return formatter_cls
