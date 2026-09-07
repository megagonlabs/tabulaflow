from collections.abc import Callable, Mapping
from typing import Any, cast

import pytest
import pandas as pd
from pydantic_ai import Tool
from pydantic_ai.tools import ToolDefinition

from tabulaflow.agents.tools.get_table_schema import GetTableSchemaTool
from tabulaflow.agents.tools.registry.get_db_document import RegistryGetDBDocumentTool
from tabulaflow.agents.tools.registry.get_schema import RegistryGetSchemaTool
from tabulaflow.agents.tools.registry.get_table_schema import RegistryGetTableSchemaTool
from tabulaflow.agents.tools.registry.run_query import RegistryRunQueryTool
from tabulaflow.core import ExecResult, RDFSchema
from tabulaflow.data.protocols import DataConnector
from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.output.specs import FixedArtifactSource
from tabulaflow.output.store import OutputStore


def _fields(tool: Tool[Any]) -> set[str]:
    tool_def = tool.tool_def
    if tool.prepare is not None:
        prepared = tool.prepare(cast(Any, None), tool_def)
        assert isinstance(prepared, ToolDefinition)
        tool_def = prepared
    return set((tool_def.parameters_json_schema.get("properties") or {}).keys())


def _db_document_tool(enable_refresh: bool) -> RegistryGetDBDocumentTool:
    return RegistryGetDBDocumentTool(
        DataConnectorRegistry(),
        db_summarizer_cls=lambda **_: None,
        enable_refresh=enable_refresh,
    )


class _RDFConnector:
    global_id = "test+rdf"
    backend = "rdf-store"
    language = "sparql"
    read_only = True

    def __init__(self) -> None:
        self.schema = RDFSchema(
            name="example",
            description="Example RDF source.",
        )

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ExecResult:
        return ExecResult(df=pd.DataFrame({"item": ["https://example.com/item/1"]}))

    async def refresh_schema_async(self) -> RDFSchema:
        return self.schema

    async def close_async(self) -> None:
        pass


_REFRESH_TOOL_FACTORIES: list[Callable[[bool], Any]] = [
    lambda enabled: GetTableSchemaTool(cast(Any, object()), cast(Any, object()), enable_refresh=enabled),
    lambda enabled: RegistryGetTableSchemaTool(DataConnectorRegistry(), cast(Any, object()), enable_refresh=enabled),
    _db_document_tool,
    lambda enabled: RegistryGetSchemaTool(DataConnectorRegistry(), enable_refresh=enabled),
]


@pytest.mark.parametrize("factory", _REFRESH_TOOL_FACTORIES)
def test_refresh_parameter_is_exposed_only_when_enabled(factory: Callable[[bool], Any]) -> None:
    disabled = _fields(factory(False).as_pydantic_ai_tool())
    enabled = _fields(factory(True).as_pydantic_ai_tool())

    assert "refresh" not in disabled
    assert enabled == disabled | {"refresh"}


@pytest.mark.parametrize(
    ("enable_params", "enable_refresh", "enable_media", "expected"),
    [
        (False, False, False, {"connector_alias", "query"}),
        (True, False, False, {"connector_alias", "query", "parameters"}),
        (False, True, False, {"connector_alias", "query", "refresh"}),
        (False, False, True, {"connector_alias", "query", "include_media"}),
        (True, True, True, {"connector_alias", "query", "parameters", "refresh", "include_media"}),
    ],
)
def test_registry_run_query_exposes_enabled_parameters(
    enable_params: bool,
    enable_refresh: bool,
    enable_media: bool,
    expected: set[str],
) -> None:
    tool = RegistryRunQueryTool(
        DataConnectorRegistry(),
        enable_params=enable_params,
        enable_refresh=enable_refresh,
        enable_media=enable_media,
    )

    assert _fields(tool.as_pydantic_ai_tool()) == expected


async def test_rdf_connector_works_through_generic_schema_and_query_tools() -> None:
    registry = DataConnectorRegistry()
    connector = _RDFConnector()
    registry.register("rdf", cast(DataConnector, connector))

    schema_text = await RegistryGetSchemaTool(registry).execute("rdf")
    document_text = await RegistryGetDBDocumentTool(
        registry,
        db_summarizer_cls=lambda **_: None,
    ).execute("rdf")

    assert "Declare any required prefixes in the SPARQL query." in schema_text
    assert "<db_schema>" in document_text
    assert "Example RDF source." in document_text

    output_store = OutputStore()
    result = await RegistryRunQueryTool(registry, output_store=output_store)(
        "rdf", "SELECT ?item WHERE { ?item a <https://example.com/Thing> }"
    )

    assert isinstance(result.return_value, str)
    assert result.return_value.startswith("[source_id=S1]")
    source = output_store.get_artifact_source("S1")
    assert isinstance(source, FixedArtifactSource)
    materialized = await output_store.get_result(source.result_id)
    assert materialized.metadata.query_language == "sparql"
    assert materialized.df is not None
    assert materialized.df["item"].tolist() == ["https://example.com/item/1"]
