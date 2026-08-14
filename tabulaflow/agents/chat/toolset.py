"""Typed default tool bundle for a chat session."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.tools import (
        AddCanonicalNameTool,
        ApplyPatchTool,
        ConnectDataSourceTool,
        CreateParameterizedSourceTool,
        ExecuteBashTool,
        ExtractRowsFromDocumentsTool,
        FileEditorTool,
        RegistryGetColumnJsonSchemaTool,
        RegistryGetDBDocumentTool,
        RegistryGetTableSchemaTool,
        RegistryRunQueryTool,
        RegistryTransferSourceTableTool,
        RenderChartTool,
        RenderGraphTool,
        RenderMapTool,
        RunSubagentForEachRowTool,
        ShowArtifactsTool,
        WebBrowserTool,
    )


@dataclass
class ChatToolset:
    run_query: RegistryRunQueryTool
    create_parameterized_source: CreateParameterizedSourceTool
    get_db_document: RegistryGetDBDocumentTool
    get_table_schema: RegistryGetTableSchemaTool
    get_column_json_schema: RegistryGetColumnJsonSchemaTool
    transfer_source_table: RegistryTransferSourceTableTool
    run_subagent_for_each_row: RunSubagentForEachRowTool | None
    extract_rows_from_documents: ExtractRowsFromDocumentsTool | None
    connect_data_source: ConnectDataSourceTool | None
    bash: ExecuteBashTool | None
    file_editor: FileEditorTool | None
    apply_patch: ApplyPatchTool | None
    add_canonical_name: AddCanonicalNameTool
    render_chart: RenderChartTool
    render_graph: RenderGraphTool
    render_map: RenderMapTool
    show_artifacts: ShowArtifactsTool
    web_browser: WebBrowserTool

    def __iter__(self) -> Iterator[Any]:
        for tool_field in fields(self):
            tool = getattr(self, tool_field.name)
            if tool is not None:
                yield tool
