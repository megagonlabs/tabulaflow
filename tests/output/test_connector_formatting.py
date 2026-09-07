from types import SimpleNamespace
from typing import Any, cast

from tabulaflow.core import NodeSchema, PropertyGraphSchema, RDFSchema, RelationshipSchema, SQLSchema, SQLTableSchema
from tabulaflow.data.protocols import DataConnector
from tabulaflow.output.formatting import format_connector_summary


def test_format_sql_connector_summary() -> None:
    connector = SimpleNamespace(
        backend="duckdb",
        language="duckdb",
        schema=SQLSchema(
            display_name="test",
            dialect="duckdb",
            tables=[
                SQLTableSchema(name="a", is_view=False, columns=[], primary_key=[], foreign_keys=[]),
                SQLTableSchema(name="b", is_view=False, columns=[], primary_key=[], foreign_keys=[]),
            ],
        ),
    )

    assert format_connector_summary(cast(DataConnector, connector)) == "duckdb, 2 tables"


def test_format_graph_connector_summary() -> None:
    connector: Any = SimpleNamespace(
        backend="neo4j",
        language="cypher",
        schema=PropertyGraphSchema(
            display_name="test",
            nodes=[NodeSchema(label="Person")],
            relationships=[RelationshipSchema(label="KNOWS"), RelationshipSchema(label="WORKS_AT")],
        ),
    )

    assert format_connector_summary(connector) == "neo4j, cypher, 1 label, 2 relationship types"


def test_format_rdf_connector_summary() -> None:
    connector: Any = SimpleNamespace(
        backend="wikidata-query-service",
        language="sparql",
        schema=RDFSchema(display_name="wikidata"),
    )

    assert format_connector_summary(connector) == "wikidata-query-service, sparql"
