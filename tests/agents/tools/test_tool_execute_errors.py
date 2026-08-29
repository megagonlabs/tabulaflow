from pathlib import Path
from typing import Any, cast

import pytest

from tabulaflow.agents.tools.add_canonical_name import AddCanonicalNameTool
from tabulaflow.agents.tools.connect_data_source import ConnectDataSourceTool
from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
from tabulaflow.data.registry import DBRegistry


async def test_canonicalization_execute_raises_without_workspace() -> None:
    tool = AddCanonicalNameTool()

    with pytest.raises(RuntimeError, match="no workspace"):
        await tool.execute(
            None,
            "items",
            canonical_column="canonical",
            instruction="Canonicalize names",
            input_column="name",
        )


async def test_connect_execute_raises_for_invalid_alias(tmp_path: Path) -> None:
    tool = ConnectDataSourceTool(DBRegistry(), tmp_path)

    with pytest.raises(ValueError, match="invalid alias"):
        await tool.execute("missing.csv", "bad-alias")

    assert (await tool("missing.csv", "bad-alias")).startswith("(error: invalid alias")


async def test_extraction_execute_raises_for_empty_output_columns() -> None:
    tool = ExtractRowsFromDocumentsTool(cast(Any, object()))

    with pytest.raises(ValueError, match="output_columns"):
        await tool.execute(
            None,
            "items",
            task_query="SELECT content FROM docs",
            task_instruction="Extract items",
            output_columns=[],
        )


async def test_subagent_execute_raises_for_empty_output_columns() -> None:
    tool = RunSubagentForEachRowTool(cast(Any, object()))

    with pytest.raises(ValueError, match="output_columns"):
        await tool.execute(
            None,
            "items",
            task_query="SELECT * FROM items",
            task_instruction="Classify {{ value }}",
            key_columns=["id"],
            output_columns=[],
        )
