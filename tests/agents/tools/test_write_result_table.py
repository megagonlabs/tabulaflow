from __future__ import annotations

from pathlib import Path

import pandas as pd

from tabulaflow.agents.tools.registry.write_result_table import WriteResultTableTool
from tabulaflow.core.results import ExecResult
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.output.store import OutputStore


async def test_write_result_table_preserves_blobs_and_creates_by_default(tmp_path: Path) -> None:
    workspace = await SQLConnector.from_url_async(
        global_id="test_transfer_workspace",
        url=f"duckdb:///{tmp_path / 'workspace.duckdb'}",
        display_name="workspace",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    registry = DataConnectorRegistry()
    registry.register("workspace", workspace)
    output_store = OutputStore()
    payloads = [b"\x89PNG\r\n\x1a\nimage", b"%PDF-1.7\ndocument"]
    source = await output_store.add_fixed_artifact_source(
        "sample_data",
        "duckdb",
        "SELECT * FROM expense_documents",
        ExecResult(df=pd.DataFrame({"id": [1, 2], "content": payloads})),
    )

    summary = await WriteResultTableTool(registry, output_store).execute(
        source.id,
        "workspace",
        None,
        "expense_documents",
    )

    assert "mode=create" in summary
    schema = await workspace.run_query_async("DESCRIBE expense_documents")
    assert schema.error is None and schema.df is not None
    assert dict(zip(schema.df["column_name"], schema.df["column_type"]))["content"] == "BLOB"
    result = await workspace.run_query_async("SELECT content FROM expense_documents ORDER BY id")
    assert result.error is None and result.df is not None
    assert result.df["content"].tolist() == payloads
