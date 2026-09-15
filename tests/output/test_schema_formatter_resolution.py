"""Defaults and compatibility checks for registered schema formatters."""

from typing import ClassVar, cast

import pytest

from tabulaflow.core import PropertyGraphSchema, RDFSchema, SchemaKind, SQLSchema
from tabulaflow.output.formatting import (
    CypherSchemaFormatter,
    SQLCompactSchemaFormatter,
    get_schema_formatter_class,
    schema_formatter_registry,
)


@pytest.mark.parametrize(
    ("schema", "expected_name", "expected_text"),
    [
        (SQLSchema(display_name="shop", tables=[]), "sql_ddl", "**Data source:** `shop`"),
        (PropertyGraphSchema(display_name="movies"), "cypher", "Node properties:"),
        (RDFSchema(display_name="knowledge"), "sparql", "Query language: sparql"),
    ],
)
def test_default_formatter_renders_its_schema(
    schema: SQLSchema | PropertyGraphSchema | RDFSchema, expected_name: str, expected_text: str
) -> None:
    if schema.kind == "sql":
        formatter = get_schema_formatter_class(schema.kind)()
        rendered = formatter.format(schema)
        actual_name = formatter.name
    elif schema.kind == "property_graph":
        graph_formatter = get_schema_formatter_class(schema.kind)()
        rendered = graph_formatter.format(schema)
        actual_name = graph_formatter.name
    else:
        rdf_formatter = get_schema_formatter_class(schema.kind)()
        rendered = rdf_formatter.format(schema)
        actual_name = rdf_formatter.name
    assert actual_name == expected_name
    assert expected_text in rendered


def test_explicit_sql_formatter() -> None:
    assert get_schema_formatter_class("sql", "sql_compact") is SQLCompactSchemaFormatter


@pytest.mark.parametrize("name", ["missing", ""])
def test_unknown_formatter_is_not_replaced_with_default(name: str) -> None:
    with pytest.raises(ValueError, match="unknown formatter"):
        get_schema_formatter_class("sql", name)


@pytest.mark.parametrize(
    ("kind", "name"),
    [("sql", "cypher"), ("property_graph", "sql_compact"), ("rdf", "sql_ddl")],
)
def test_incompatible_override_fails(kind: SchemaKind, name: str) -> None:
    with pytest.raises(ValueError, match=f"not {kind!r}"):
        get_schema_formatter_class(kind, name)


def test_unknown_schema_kind_fails() -> None:
    with pytest.raises(ValueError, match="Unknown schema kind: 'neo4j'"):
        get_schema_formatter_class(cast(SchemaKind, "neo4j"))


def test_custom_formatter_is_selected_without_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    class CustomGraphFormatter(CypherSchemaFormatter):
        name: ClassVar[str] = "test_custom_graph"

        def __init__(self, prefix: str) -> None:
            self.prefix = prefix

        def format(self, schema: PropertyGraphSchema) -> str:
            return f"{self.prefix}: {schema.display_name}"

    monkeypatch.setattr(schema_formatter_registry, "_classes", schema_formatter_registry._classes.copy())
    schema_formatter_registry.register(CustomGraphFormatter)

    formatter_cls = get_schema_formatter_class("property_graph", "test_custom_graph")
    assert formatter_cls is CustomGraphFormatter
    formatter = CustomGraphFormatter(prefix="selected")
    assert formatter.format(PropertyGraphSchema(display_name="movies")) == "selected: movies"
    with pytest.raises(ValueError, match="supports 'property_graph', not 'sql'"):
        get_schema_formatter_class("sql", "test_custom_graph")
