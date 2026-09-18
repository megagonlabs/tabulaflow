from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tabulaflow.agents.tools.add_canonical_name import AddCanonicalNameTool
from tabulaflow.agents.tools.connect_data_source import ConnectDataSourceTool
from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
from tabulaflow.core import RDFSchema
from tabulaflow.data.registry import DataConnectorRegistry


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
    tool = ConnectDataSourceTool(DataConnectorRegistry(), tmp_path)

    with pytest.raises(ValueError, match="invalid alias"):
        await tool.execute("missing.csv", "bad-alias")

    assert (await tool("missing.csv", "bad-alias")).startswith("(error: invalid alias")


async def test_connect_reports_rdf_source_without_calling_it_sql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connector = SimpleNamespace(
        backend="sparql",
        language="sparql",
        global_id="test-rdf",
        schema=RDFSchema(display_name="example"),
    )

    async def connect_data_source(*args: object, **kwargs: object) -> object:
        return connector

    monkeypatch.setattr("tabulaflow.agents.tools.connect_data_source.connect_data_source", connect_data_source)
    tool = ConnectDataSourceTool(DataConnectorRegistry(), tmp_path)

    result = await tool.execute("sparql+https://example.test/query", "example")

    assert result == "Connected 'example' (sparql). Query it using the alias 'example'."
    assert "SQL" not in result


async def test_connect_error_does_not_expose_url_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def connect_data_source(*args: object, **kwargs: object) -> object:
        raise RuntimeError("connection refused")

    monkeypatch.setattr("tabulaflow.agents.tools.connect_data_source.connect_data_source", connect_data_source)
    tool = ConnectDataSourceTool(DataConnectorRegistry(), tmp_path)

    result = await tool("sparql+https://alice:p%40ss@example.test/query", "example")

    assert "p%40ss" not in result
    assert "sparql+https://alice:***@example.test/query" in result
    assert "connection refused" in result
    assert "needs credentials" not in result


async def test_connect_catalog_source_returns_curated_guidance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    connector = SimpleNamespace(
        backend="sparql",
        language="sparql",
        global_id="test-rdf",
        schema=RDFSchema(display_name="wikidata"),
    )

    async def connect_data_source(*args: object, **kwargs: object) -> object:
        return connector

    monkeypatch.setattr("tabulaflow.agents.tools.connect_data_source.connect_data_source", connect_data_source)
    tool = ConnectDataSourceTool(DataConnectorRegistry(), tmp_path)

    result = await tool.execute("wikidata", "wikidata")

    assert "en,mul" in result
    assert "LANG(?label) IN" in result
    assert "user's requested language" in result
    assert "get_data_source_document" in result


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
