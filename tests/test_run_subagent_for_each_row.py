"""Tests for RunSubagentForEachRowTool — key validation and write-back error surfacing.

The per-row subagent LLM is stubbed with a ``FunctionModel`` returning a fixed
text value, so the tests assert on validation and write-back behavior rather
than any model behavior.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import AsyncGenerator

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.toolhub.run_subagent_for_each_row import RunSubagentForEachRowTool


def _const(text: str):
    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return fn


def _ctx() -> SimpleNamespace:
    return SimpleNamespace(tool_call_id="test-call")


async def _rows(conn: SQLConnector, query: str) -> list[dict]:
    res = await conn.run_query_async(query)
    assert res.error is None and res.df is not None, res.error
    return res.df.to_dict(orient="records")


@pytest.fixture
async def conn(tmp_path: Path) -> AsyncGenerator[SQLConnector, None]:
    db_path = tmp_path / "workspace.duckdb"
    connector = await SQLConnector.from_url_async(
        global_id="test-workspace",
        url=f"duckdb:///{db_path}",
        db_name="workspace",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    yield connector


def _tool(conn: SQLConnector, text: str = "OUT", *, store_metadata: bool = False) -> RunSubagentForEachRowTool:
    return RunSubagentForEachRowTool(conn, subagent_llm=FunctionModel(_const(text)), store_metadata=store_metadata)


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_writes_each_row(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INTEGER, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,NULL),(2,NULL),(3,NULL)")

        summary = await _tool(conn, "DONE").__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=["id"],
            output_columns=["label"],
        )
        assert "succeeded for 3 rows, failed for 0 rows" in summary
        assert [r["label"] for r in await _rows(conn, "SELECT label FROM t")] == ["DONE", "DONE", "DONE"]


class TestWriteBackErrorSurfaced:
    @pytest.mark.asyncio
    async def test_integer_output_column_rejects_text_and_is_reported(self, conn: SQLConnector) -> None:
        # Real-world failure: an all-NULL untyped column from VALUES is inferred
        # INTEGER, so writing the subagent's text output fails. The error must be
        # surfaced (row counted as failed), not silently swallowed as success.
        await conn.run_query_async(
            "CREATE TABLE t AS SELECT * FROM (VALUES (1, NULL), (2, NULL)) AS v(id, page_message_id)"
        )
        assert "INTEGER" in str(await conn.run_query_async("DESCRIBE t"))

        summary = await _tool(conn, "M123", store_metadata=True).__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT id FROM t",
            task_instruction="x",
            key_columns=["id"],
            output_columns=["page_message_id"],
        )
        assert "succeeded for 0 rows, failed for 2 rows" in summary
        assert "write-back failed" in summary
        # The failure is recorded per-row, and the value stays unwritten (NULL).
        rows = await _rows(conn, "SELECT page_message_id, _subagent_exception FROM t")
        assert all(r["page_message_id"] is None for r in rows)
        assert all(r["_subagent_exception"] and "write-back failed" in r["_subagent_exception"] for r in rows)


class TestKeyValidation:
    @pytest.mark.asyncio
    async def test_empty_key_rejected(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INTEGER, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,NULL)")
        summary = await _tool(conn).__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=[],
            output_columns=["label"],
        )
        assert summary.startswith("(error:") and "non-empty" in summary

    @pytest.mark.asyncio
    async def test_non_unique_key_rejected(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(grp VARCHAR, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES ('a',NULL),('a',NULL),('b',NULL)")
        summary = await _tool(conn).__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=["grp"],
            output_columns=["label"],
        )
        assert summary.startswith("(error:") and "not unique" in summary
        # Nothing written — rejected before fan-out.
        assert all(r["label"] is None for r in await _rows(conn, "SELECT label FROM t"))

    @pytest.mark.asyncio
    async def test_null_key_rejected(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INTEGER, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,NULL),(NULL,NULL)")
        summary = await _tool(conn).__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=["id"],
            output_columns=["label"],
        )
        assert summary.startswith("(error:") and "NULL" in summary

    @pytest.mark.asyncio
    async def test_key_not_a_table_column_rejected(self, conn: SQLConnector) -> None:
        # A key projected from a joined table (not a column of the target) can't
        # address target rows on write-back.
        await conn.run_query_async("CREATE TABLE t(id INTEGER, label VARCHAR)")
        await conn.run_query_async("CREATE TABLE meta(id INTEGER, tag VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,NULL),(2,NULL)")
        await conn.run_query_async("INSERT INTO meta VALUES (1,'x'),(2,'y')")
        summary = await _tool(conn).__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT t.id, m.tag FROM t JOIN meta m ON t.id = m.id",
            task_instruction="x",
            key_columns=["tag"],
            output_columns=["label"],
        )
        assert summary.startswith("(error:") and "tag" in summary
