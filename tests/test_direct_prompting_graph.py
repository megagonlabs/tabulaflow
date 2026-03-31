"""Tests for DirectPrompting with property-graph (Neo4j) schemas."""

from mintq.agenthub.direct_prompting import DirectPrompting
from mintq.agenthub.utils import BasicAgentConfig
from mintq.schema import NodeSchema, PropertyGraphSchema


def test_direct_prompting_formats_property_graph_schema() -> None:
    cfg = BasicAgentConfig(
        compress_schema=False,
        schema_formatter="cypher",
        use_column_description=False,
    )
    dp = DirectPrompting(cfg)

    class _FakeGraphConn:
        schema = PropertyGraphSchema(
            name="g",
            nodes=[NodeSchema(label="Person", properties=[])],
            relationships=[],
        )
        language = "cypher"

    text = dp._format_schema_for_prompt(_FakeGraphConn())  # type: ignore[arg-type]
    assert "Person" in text
    assert "cypher" in text.lower()


def test_direct_prompting_property_graph_ignores_sql_formatter_name() -> None:
    """If schema_formatter is SQL-only, fall back to cypher for property graphs."""
    cfg = BasicAgentConfig(
        compress_schema=False,
        schema_formatter="sql_ddl",
        use_column_description=False,
    )
    dp = DirectPrompting(cfg)

    class _FakeGraphConn:
        schema = PropertyGraphSchema(name="g", nodes=[NodeSchema(label="N", properties=[])], relationships=[])
        language = "cypher"

    text = dp._format_schema_for_prompt(_FakeGraphConn())  # type: ignore[arg-type]
    assert "N" in text
