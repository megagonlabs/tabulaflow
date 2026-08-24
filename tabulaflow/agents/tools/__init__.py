"""Model-facing agent tools."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.tools.add_canonical_name import AddCanonicalNameTool
    from tabulaflow.agents.tools.apply_patch import ApplyPatchTool
    from tabulaflow.agents.tools.base import (
        BaseTool,
        LLMProfileTool,
        ProgressReportingTool,
        ToolCallOutcome,
        ToolProgressUpdate,
    )
    from tabulaflow.agents.tools.connect_data_source import ConnectDataSourceTool
    from tabulaflow.agents.tools.create_parameterized_source import CreateParameterizedSourceTool
    from tabulaflow.agents.tools.entity_extractor import EntityExtractor
    from tabulaflow.agents.tools.execute_bash import BashToolMetrics, ExecuteBashTool
    from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
    from tabulaflow.agents.tools.file_editor import FileEditorRoot, FileEditorTool, FileEditorToolMetrics
    from tabulaflow.agents.tools.get_column_json_schema import GetColumnJsonSchemaTool
    from tabulaflow.agents.tools.get_table_schema import GetTableSchemaTool
    from tabulaflow.agents.tools.registry_get_column_json_schema import RegistryGetColumnJsonSchemaTool
    from tabulaflow.agents.tools.registry_get_db_document import RegistryGetDBDocumentTool
    from tabulaflow.agents.tools.registry_get_schema import RegistryGetSchemaTool
    from tabulaflow.agents.tools.registry_get_table_schema import RegistryGetTableSchemaTool
    from tabulaflow.agents.tools.registry_run_query import RegistryRunQueryTool
    from tabulaflow.agents.tools.registry_transfer_source_table import RegistryTransferSourceTableTool
    from tabulaflow.agents.tools.render_chart import RenderChartTool
    from tabulaflow.agents.tools.render_graph import RenderGraphTool
    from tabulaflow.agents.tools.render_map import RenderMapTool
    from tabulaflow.agents.tools.run_query import RunQueryTool
    from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
    from tabulaflow.agents.tools.show_artifacts import ArtifactBundle, ArtifactRef, ShowArtifactsTool
    from tabulaflow.agents.tools.web_browser import WebBrowserManager, WebBrowserTool

_LAZY_EXPORTS = {
    "AddCanonicalNameTool": ("tabulaflow.agents.tools.add_canonical_name", "AddCanonicalNameTool"),
    "ApplyPatchTool": ("tabulaflow.agents.tools.apply_patch", "ApplyPatchTool"),
    "ArtifactBundle": ("tabulaflow.agents.tools.show_artifacts", "ArtifactBundle"),
    "ArtifactRef": ("tabulaflow.agents.tools.show_artifacts", "ArtifactRef"),
    "BaseTool": ("tabulaflow.agents.tools.base", "BaseTool"),
    "BashToolMetrics": ("tabulaflow.agents.tools.execute_bash", "BashToolMetrics"),
    "ConnectDataSourceTool": ("tabulaflow.agents.tools.connect_data_source", "ConnectDataSourceTool"),
    "CreateParameterizedSourceTool": (
        "tabulaflow.agents.tools.create_parameterized_source",
        "CreateParameterizedSourceTool",
    ),
    "EntityExtractor": ("tabulaflow.agents.tools.entity_extractor", "EntityExtractor"),
    "ExecuteBashTool": ("tabulaflow.agents.tools.execute_bash", "ExecuteBashTool"),
    "ExtractRowsFromDocumentsTool": (
        "tabulaflow.agents.tools.extract_rows_from_documents",
        "ExtractRowsFromDocumentsTool",
    ),
    "FileEditorRoot": ("tabulaflow.agents.tools.file_editor", "FileEditorRoot"),
    "FileEditorTool": ("tabulaflow.agents.tools.file_editor", "FileEditorTool"),
    "FileEditorToolMetrics": ("tabulaflow.agents.tools.file_editor", "FileEditorToolMetrics"),
    "GetColumnJsonSchemaTool": (
        "tabulaflow.agents.tools.get_column_json_schema",
        "GetColumnJsonSchemaTool",
    ),
    "GetTableSchemaTool": ("tabulaflow.agents.tools.get_table_schema", "GetTableSchemaTool"),
    "LLMProfileTool": ("tabulaflow.agents.tools.base", "LLMProfileTool"),
    "ProgressReportingTool": ("tabulaflow.agents.tools.base", "ProgressReportingTool"),
    "RegistryGetColumnJsonSchemaTool": (
        "tabulaflow.agents.tools.registry_get_column_json_schema",
        "RegistryGetColumnJsonSchemaTool",
    ),
    "RegistryGetDBDocumentTool": (
        "tabulaflow.agents.tools.registry_get_db_document",
        "RegistryGetDBDocumentTool",
    ),
    "RegistryGetSchemaTool": ("tabulaflow.agents.tools.registry_get_schema", "RegistryGetSchemaTool"),
    "RegistryGetTableSchemaTool": (
        "tabulaflow.agents.tools.registry_get_table_schema",
        "RegistryGetTableSchemaTool",
    ),
    "RegistryRunQueryTool": ("tabulaflow.agents.tools.registry_run_query", "RegistryRunQueryTool"),
    "RegistryTransferSourceTableTool": (
        "tabulaflow.agents.tools.registry_transfer_source_table",
        "RegistryTransferSourceTableTool",
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
    "ToolCallOutcome": ("tabulaflow.agents.tools.base", "ToolCallOutcome"),
    "ToolProgressUpdate": ("tabulaflow.agents.tools.base", "ToolProgressUpdate"),
    "WebBrowserManager": ("tabulaflow.agents.tools.web_browser", "WebBrowserManager"),
    "WebBrowserTool": ("tabulaflow.agents.tools.web_browser", "WebBrowserTool"),
}

__all__ = [
    "AddCanonicalNameTool",
    "ApplyPatchTool",
    "ArtifactBundle",
    "ArtifactRef",
    "BaseTool",
    "BashToolMetrics",
    "ConnectDataSourceTool",
    "CreateParameterizedSourceTool",
    "EntityExtractor",
    "ExecuteBashTool",
    "ExtractRowsFromDocumentsTool",
    "FileEditorRoot",
    "FileEditorTool",
    "FileEditorToolMetrics",
    "GetColumnJsonSchemaTool",
    "GetTableSchemaTool",
    "LLMProfileTool",
    "ProgressReportingTool",
    "RegistryGetColumnJsonSchemaTool",
    "RegistryGetDBDocumentTool",
    "RegistryGetSchemaTool",
    "RegistryGetTableSchemaTool",
    "RegistryRunQueryTool",
    "RegistryTransferSourceTableTool",
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
