"""Model-facing agent tools."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.tools.add_canonical_name import AddCanonicalNameTool
    from tabulaflow.agents.tools.filesystem.access import FilesystemRoot
    from tabulaflow.agents.tools.filesystem.edit import EditFileTool, EditFileToolMetrics
    from tabulaflow.agents.tools.filesystem.view import ViewTool, ViewToolMetrics
    from tabulaflow.agents.tools.filesystem.patch import ApplyPatchTool
    from tabulaflow.agents.tools.protocols import (
        AgentTool,
        LLMProfileTool,
        ProgressReportingTool,
        ToolCallOutcome,
        ToolProgressUpdate,
    )
    from tabulaflow.agents.tools.connect_data_source import ConnectDataSourceTool
    from tabulaflow.agents.tools.create_parameterized_source import CreateParameterizedSourceTool
    from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
    from tabulaflow.agents.tools.shell.tool import BashToolMetrics, ExecuteBashTool
    from tabulaflow.agents.tools.get_column_json_schema import GetColumnJsonSchemaTool
    from tabulaflow.agents.tools.get_table_schema import GetTableSchemaTool
    from tabulaflow.agents.tools.registry.get_column_json_schema import RegistryGetColumnJsonSchemaTool
    from tabulaflow.agents.tools.registry.get_db_document import RegistryGetDBDocumentTool
    from tabulaflow.agents.tools.registry.get_schema import RegistryGetSchemaTool
    from tabulaflow.agents.tools.registry.get_table_schema import RegistryGetTableSchemaTool
    from tabulaflow.agents.tools.registry.run_query import RegistryRunQueryTool
    from tabulaflow.agents.tools.registry.transfer_source_table import TransferSourceTableTool
    from tabulaflow.agents.tools.render_chart import RenderChartTool
    from tabulaflow.agents.tools.render_graph import RenderGraphTool
    from tabulaflow.agents.tools.render_map import RenderMapTool
    from tabulaflow.agents.tools.run_query import RunQueryTool
    from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
    from tabulaflow.agents.tools.show_artifacts import ArtifactBundle, ArtifactRef, ShowArtifactsTool
    from tabulaflow.agents.tools.browser.manager import WebBrowserManager
    from tabulaflow.agents.tools.browser.tool import WebBrowserTool

_LAZY_EXPORTS = {
    "AddCanonicalNameTool": ("tabulaflow.agents.tools.add_canonical_name", "AddCanonicalNameTool"),
    "ApplyPatchTool": ("tabulaflow.agents.tools.filesystem.patch", "ApplyPatchTool"),
    "ArtifactBundle": ("tabulaflow.agents.tools.show_artifacts", "ArtifactBundle"),
    "ArtifactRef": ("tabulaflow.agents.tools.show_artifacts", "ArtifactRef"),
    "AgentTool": ("tabulaflow.agents.tools.protocols", "AgentTool"),
    "BashToolMetrics": ("tabulaflow.agents.tools.shell.tool", "BashToolMetrics"),
    "ConnectDataSourceTool": ("tabulaflow.agents.tools.connect_data_source", "ConnectDataSourceTool"),
    "CreateParameterizedSourceTool": (
        "tabulaflow.agents.tools.create_parameterized_source",
        "CreateParameterizedSourceTool",
    ),
    "ExecuteBashTool": ("tabulaflow.agents.tools.shell.tool", "ExecuteBashTool"),
    "ExtractRowsFromDocumentsTool": (
        "tabulaflow.agents.tools.extract_rows_from_documents",
        "ExtractRowsFromDocumentsTool",
    ),
    "EditFileTool": ("tabulaflow.agents.tools.filesystem.edit", "EditFileTool"),
    "EditFileToolMetrics": ("tabulaflow.agents.tools.filesystem.edit", "EditFileToolMetrics"),
    "FilesystemRoot": ("tabulaflow.agents.tools.filesystem.access", "FilesystemRoot"),
    "GetColumnJsonSchemaTool": (
        "tabulaflow.agents.tools.get_column_json_schema",
        "GetColumnJsonSchemaTool",
    ),
    "GetTableSchemaTool": ("tabulaflow.agents.tools.get_table_schema", "GetTableSchemaTool"),
    "LLMProfileTool": ("tabulaflow.agents.tools.protocols", "LLMProfileTool"),
    "ProgressReportingTool": ("tabulaflow.agents.tools.protocols", "ProgressReportingTool"),
    "RegistryGetColumnJsonSchemaTool": (
        "tabulaflow.agents.tools.registry.get_column_json_schema",
        "RegistryGetColumnJsonSchemaTool",
    ),
    "RegistryGetDBDocumentTool": (
        "tabulaflow.agents.tools.registry.get_db_document",
        "RegistryGetDBDocumentTool",
    ),
    "RegistryGetSchemaTool": ("tabulaflow.agents.tools.registry.get_schema", "RegistryGetSchemaTool"),
    "RegistryGetTableSchemaTool": (
        "tabulaflow.agents.tools.registry.get_table_schema",
        "RegistryGetTableSchemaTool",
    ),
    "RegistryRunQueryTool": ("tabulaflow.agents.tools.registry.run_query", "RegistryRunQueryTool"),
    "TransferSourceTableTool": (
        "tabulaflow.agents.tools.registry.transfer_source_table",
        "TransferSourceTableTool",
    ),
    "RenderChartTool": ("tabulaflow.agents.tools.render_chart", "RenderChartTool"),
    "RenderGraphTool": ("tabulaflow.agents.tools.render_graph", "RenderGraphTool"),
    "RenderMapTool": ("tabulaflow.agents.tools.render_map", "RenderMapTool"),
    "RunQueryTool": ("tabulaflow.agents.tools.run_query", "RunQueryTool"),
    "RunSubagentForEachRowTool": (
        "tabulaflow.agents.tools.run_subagent_for_each_row",
        "RunSubagentForEachRowTool",
    ),
    "ShowArtifactsTool": ("tabulaflow.agents.tools.show_artifacts", "ShowArtifactsTool"),
    "ToolCallOutcome": ("tabulaflow.agents.tools.protocols", "ToolCallOutcome"),
    "ToolProgressUpdate": ("tabulaflow.agents.tools.protocols", "ToolProgressUpdate"),
    "WebBrowserManager": ("tabulaflow.agents.tools.browser.manager", "WebBrowserManager"),
    "WebBrowserTool": ("tabulaflow.agents.tools.browser.tool", "WebBrowserTool"),
    "ViewTool": ("tabulaflow.agents.tools.filesystem.view", "ViewTool"),
    "ViewToolMetrics": ("tabulaflow.agents.tools.filesystem.view", "ViewToolMetrics"),
}

__all__ = [
    "AddCanonicalNameTool",
    "ApplyPatchTool",
    "ArtifactBundle",
    "ArtifactRef",
    "AgentTool",
    "BashToolMetrics",
    "ConnectDataSourceTool",
    "CreateParameterizedSourceTool",
    "ExecuteBashTool",
    "ExtractRowsFromDocumentsTool",
    "EditFileTool",
    "EditFileToolMetrics",
    "FilesystemRoot",
    "GetColumnJsonSchemaTool",
    "GetTableSchemaTool",
    "LLMProfileTool",
    "ProgressReportingTool",
    "RegistryGetColumnJsonSchemaTool",
    "RegistryGetDBDocumentTool",
    "RegistryGetSchemaTool",
    "RegistryGetTableSchemaTool",
    "RegistryRunQueryTool",
    "TransferSourceTableTool",
    "RenderChartTool",
    "RenderGraphTool",
    "RenderMapTool",
    "RunQueryTool",
    "RunSubagentForEachRowTool",
    "ShowArtifactsTool",
    "ToolCallOutcome",
    "ToolProgressUpdate",
    "WebBrowserManager",
    "WebBrowserTool",
    "ViewTool",
    "ViewToolMetrics",
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
