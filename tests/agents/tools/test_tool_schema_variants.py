from collections.abc import Callable
from typing import Any, cast

import pytest
from pydantic_ai import Tool
from pydantic_ai.tools import ToolDefinition

from tabulaflow.agents.tools.get_table_schema import GetTableSchemaTool
from tabulaflow.agents.tools.registry.get_db_document import RegistryGetDBDocumentTool
from tabulaflow.agents.tools.registry.get_schema import RegistryGetSchemaTool
from tabulaflow.agents.tools.registry.get_table_schema import RegistryGetTableSchemaTool
from tabulaflow.agents.tools.registry.run_query import RegistryRunQueryTool
from tabulaflow.data.registry import DataConnectorRegistry


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
