from types import SimpleNamespace
from typing import Any, cast

from tabulaflow.data.base import DataConnector
from tabulaflow.output.formatting import format_connector_summary


def test_format_sql_connector_summary() -> None:
    connector = SimpleNamespace(
        connector_type="sql",
        language="duckdb",
        schema=SimpleNamespace(dialect="duckdb", tables=[object(), object()]),
    )

    assert format_connector_summary(cast(DataConnector, connector)) == "duckdb, 2 tables"


def test_format_graph_connector_summary() -> None:
    connector: Any = SimpleNamespace(
        connector_type="property_graph",
        backend="neo4j",
        language="cypher",
        schema=SimpleNamespace(nodes=[object()], relationships=[object(), object()]),
    )

    assert format_connector_summary(connector) == "neo4j, cypher, 1 label, 2 relationship types"
