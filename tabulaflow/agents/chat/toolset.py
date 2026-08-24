"""Typed default tool bundle for a chat session."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.tools.add_canonical_name import AddCanonicalNameTool
    from tabulaflow.agents.tools.apply_patch import ApplyPatchTool
    from tabulaflow.agents.tools.connect_data_source import ConnectDataSourceTool
    from tabulaflow.agents.tools.create_parameterized_source import CreateParameterizedSourceTool
    from tabulaflow.agents.tools.execute_bash import ExecuteBashTool
    from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
    from tabulaflow.agents.tools.file_editor import FileEditorTool
    from tabulaflow.agents.tools.registry_get_column_json_schema import RegistryGetColumnJsonSchemaTool
    from tabulaflow.agents.tools.registry_get_db_document import RegistryGetDBDocumentTool
    from tabulaflow.agents.tools.registry_get_table_schema import RegistryGetTableSchemaTool
    from tabulaflow.agents.tools.registry_run_query import RegistryRunQueryTool
    from tabulaflow.agents.tools.registry_transfer_source_table import RegistryTransferSourceTableTool
    from tabulaflow.agents.tools.render_chart import RenderChartTool
    from tabulaflow.agents.tools.render_graph import RenderGraphTool
    from tabulaflow.agents.tools.render_map import RenderMapTool
    from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
    from tabulaflow.agents.tools.show_artifacts import ShowArtifactsTool
    from tabulaflow.agents.tools.web_browser import WebBrowserTool


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
