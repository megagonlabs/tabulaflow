"""Tests for RunSubagentForEachRowTool — key validation and write-back error surfacing.

The per-row subagent LLM is stubbed with a ``FunctionModel`` that calls the
``submit_answer`` structured-output tool with a fixed value for every output column,
so the tests assert on validation and write-back behavior rather than any model
behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from collections.abc import Callable
from typing import Any, AsyncGenerator

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector
from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool


def _emit_const(value: object) -> Callable[[list[ModelMessage], AgentInfo], ModelResponse]:
    """Stub subagent: call ``submit_answer`` with every output field set to ``value``."""

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        emit = next(t for t in info.output_tools if t.name == "submit_answer")
        fields = list((emit.parameters_json_schema.get("properties") or {}).keys())
        return ModelResponse(parts=[ToolCallPart(tool_name="submit_answer", args={f: value for f in fields})])

    return fn


def _ctx() -> Any:
    return SimpleNamespace(tool_call_id="test-call")


class _AnthropicFunctionModel(FunctionModel):
    """Function model that exercises the Anthropic output-selection path."""

    @property
    def system(self) -> str:
        return "anthropic"


def _emit_native(kind: str, data: dict[str, object]) -> Callable[[list[ModelMessage], AgentInfo], ModelResponse]:
    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert info.output_tools == []
        assert info.model_request_parameters.output_mode == "native"
        payload = {"result": {"kind": kind, "data": data}}
        return ModelResponse(parts=[TextPart(content=json.dumps(payload))])

    return fn


async def _rows(conn: SQLConnector, query: str) -> list[dict[str, Any]]:
    res = await conn.run_query_async(query)
    assert res.error is None and res.df is not None, res.error
    return list(res.df.to_dict(orient="records"))


@pytest.fixture
async def conn(tmp_path: Path) -> AsyncGenerator[SQLConnector, None]:
    db_path = tmp_path / "workspace.duckdb"
    connector = await SQLConnector.from_url_async(
        global_id="test-workspace",
        url=f"duckdb:///{db_path}",
        db_name="workspace",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )
    yield connector


def _tool(conn: SQLConnector, value: object = "OUT", *, store_metadata: bool = False) -> RunSubagentForEachRowTool:
    return RunSubagentForEachRowTool(
        conn, subagent_llm=FunctionModel(_emit_const(value)), store_metadata=store_metadata
    )


class TestHappyPath:
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

    async def test_writes_multiple_typed_columns_across_types(self, conn: SQLConnector) -> None:
        # Cover the full scalar type matrix in one multi-column UPDATE: text, the three
        # integer widths (SMALLINT/INTEGER/BIGINT — note BIGINT/SMALLINT introspect to
        # the canonical BIG_INTEGER/SMALL_INTEGER tokens), float/double/decimal, bool,
        # date, timestamp, and an omitted column landing as NULL.
        await conn.run_query_async(
            "CREATE TABLE t(id INTEGER, s VARCHAR, sm SMALLINT, big BIGINT, d DOUBLE, "
            "dec DECIMAL(10,2), b BOOLEAN, dt DATE, ts TIMESTAMP, nul VARCHAR)"
        )
        await conn.run_query_async("INSERT INTO t(id) VALUES (1),(2)")
        # Refresh so output-column types resolve and submit_answer is typed accordingly.
        await conn.refresh_schema_async()

        emit = {
            "s": "hi", "sm": 7, "big": 9_999_999_999, "d": 3.5, "dec": 12.34,
            "b": True, "dt": "2024-03-15", "ts": "2024-03-15T10:30:00", "nul": None,
        }  # fmt: skip

        def stub(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart(tool_name="submit_answer", args=emit)])

        tool = RunSubagentForEachRowTool(conn, subagent_llm=FunctionModel(stub))
        summary = await tool.execute(
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=["id"],
            output_columns=["s", "sm", "big", "d", "dec", "b", "dt", "ts", "nul"],
        )
        assert "succeeded for 2 rows, failed for 0 rows" in summary

        import datetime
        from decimal import Decimal

        row = (await _rows(conn, "SELECT * FROM t ORDER BY id"))[0]
        assert row["s"] == "hi"
        assert row["sm"] == 7 and row["big"] == 9_999_999_999
        assert row["d"] == 3.5 and row["dec"] == Decimal("12.34")
        assert row["b"] is True
        assert row["dt"] == datetime.date(2024, 3, 15)
        assert row["ts"] == datetime.datetime(2024, 3, 15, 10, 30, 0)
        assert row["nul"] is None

    async def test_anthropic_uses_native_output_with_thinking(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INTEGER, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,NULL)")
        model = _AnthropicFunctionModel(_emit_native("Answer", {"label": "DONE"}))
        tool = RunSubagentForEachRowTool(conn, subagent_llm=model, model_settings={"thinking": "high"})

        summary = await tool.__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=["id"],
            output_columns=["label"],
        )

        assert "succeeded for 1 rows, failed for 0 rows" in summary
        assert await _rows(conn, "SELECT label FROM t") == [{"label": "DONE"}]

    async def test_anthropic_native_abort_is_recorded(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INTEGER, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,NULL)")
        model = _AnthropicFunctionModel(_emit_native("AbortTask", {"message": "missing source"}))
        tool = RunSubagentForEachRowTool(
            conn,
            subagent_llm=model,
            model_settings={"thinking": "high"},
            store_metadata=True,
        )

        summary = await tool.__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=["id"],
            output_columns=["label"],
        )

        assert "succeeded for 0 rows, failed for 1 rows" in summary
        rows = await _rows(conn, "SELECT label, _subagent_exception FROM t")
        assert rows == [{"label": None, "_subagent_exception": "AbortTask: missing source"}]


class TestWriteBackErrorSurfaced:
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


class TestTemplateValidation:
    async def test_unknown_placeholder_rejected_up_front(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INTEGER, txt VARCHAR, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,'a',NULL)")
        # A direct typo and the otherwise-silent ``default(...)`` form are both caught
        # before any fan-out; nothing is written.
        for instr in ("do {{ txtt }}", "do {{ foo | default('') }}"):
            summary = await _tool(conn).__call__(
                _ctx(),
                None,
                "t",
                task_query="SELECT id, txt FROM t",
                task_instruction=instr,
                key_columns=["id"],
                output_columns=["label"],
            )
            assert summary.startswith("(error:") and "not in the task_query result" in summary
        assert all(r["label"] is None for r in await _rows(conn, "SELECT label FROM t"))

    async def test_valid_placeholder_accepted(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INTEGER, txt VARCHAR, label VARCHAR)")
        await conn.run_query_async("INSERT INTO t VALUES (1,'a',NULL)")
        summary = await _tool(conn, "DONE").__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT id, txt FROM t",
            task_instruction="classify {{ txt }}",
            key_columns=["id"],
            output_columns=["label"],
        )
        assert "succeeded for 1 rows" in summary
