"""Affected-row count: connector plumbing, run_query messaging, and the
write-back zero-match guard it enables in run_subagent_for_each_row."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from collections.abc import Callable
from typing import Any, AsyncGenerator

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from tabulaflow.data.sql import SQLConnector
from tabulaflow.agents.tools.run_query import RunQueryTool
from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool


@pytest.fixture
async def conn(tmp_path: Path) -> AsyncGenerator[SQLConnector, None]:
    connector = await SQLConnector.from_url_async(
        global_id="test-affected",
        url=f"duckdb:///{tmp_path / 'w.duckdb'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    yield connector


@pytest.fixture
async def sqlite_conn(tmp_path: Path) -> AsyncGenerator[SQLConnector, None]:
    # aiosqlite is an async engine — exercises the async execute path.
    connector = await SQLConnector.from_url_async(
        global_id="test-affected-sqlite",
        url=f"sqlite+aiosqlite:///{tmp_path / 't.sqlite'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    yield connector


class TestAsyncEngineDML:
    @pytest.mark.asyncio
    async def test_sqlalchemy_dml_executable_on_async_engine(self, sqlite_conn: SQLConnector) -> None:
        # A SQLAlchemy update() Executable on an async engine must not be streamed
        # (it returns no rows); regression for "This result object does not return rows".
        import sqlalchemy

        from tabulaflow.agents.tools.engines.sql import sa_table

        await sqlite_conn.run_query_async("CREATE TABLE t(id INTEGER, v INTEGER)")
        await sqlite_conn.run_query_async("INSERT INTO t VALUES (1,0),(2,0),(3,0)")

        sa_t = sa_table(None, "t", "id", "v")
        stmt = sqlalchemy.update(sa_t).where(sa_t.c["id"] <= 2).values({sa_t.c["v"]: 9})
        r = await sqlite_conn.run_query_async(stmt)
        assert r.succeeded and r.df is None and r.affected_rows == 2

        # raw-string DML and SELECT still work on the async engine.
        r0 = await sqlite_conn.run_query_async("UPDATE t SET v=1 WHERE id=999")
        assert r0.succeeded and r0.df is None and r0.affected_rows == 0
        rs = await sqlite_conn.run_query_async("SELECT * FROM t")
        assert rs.df is not None and len(rs.df) == 3


class TestConnectorAffectedRows:
    @pytest.mark.asyncio
    async def test_counts_by_statement_kind(self, conn: SQLConnector) -> None:
        async def run(sql: str) -> Any:
            return await conn.run_query_async(sql)

        # Non-row statements: success carried by error-is-None, df is None.
        # DDL: no count.
        r = await run("CREATE TABLE t(id INT, v INT)")
        assert r.affected_rows is None and r.df is None and r.succeeded

        r = await run("INSERT INTO t VALUES (1,10),(2,20),(3,30)")
        assert r.affected_rows == 3 and r.df is None and r.succeeded

        r = await run("UPDATE t SET v=99 WHERE id<=2")
        assert r.affected_rows == 2 and r.df is None

        # 0 affected is reported as 0 (a no-op), not None.
        r = await run("UPDATE t SET v=0 WHERE id=999")
        assert r.affected_rows == 0 and r.df is None and r.succeeded

        r = await run("DELETE FROM t WHERE id=3")
        assert r.affected_rows == 1 and r.df is None

    @pytest.mark.asyncio
    async def test_select_has_no_count_and_count_alias_not_misread(self, conn: SQLConnector) -> None:
        await conn.run_query_async("CREATE TABLE t(id INT)")
        await conn.run_query_async("INSERT INTO t VALUES (1),(2)")

        r = await conn.run_query_async("SELECT * FROM t")
        assert r.affected_rows is None and r.df is not None and len(r.df) == 2

        # A SELECT that aliases a column to "Count" must stay a row result, not be
        # mistaken for a driver write-count.
        r = await conn.run_query_async('SELECT count(*) AS "Count" FROM t')
        assert r.affected_rows is None and r.df is not None
        assert r.df.to_dict("records") == [{"Count": 2}]

    @pytest.mark.asyncio
    async def test_error_is_not_succeeded_and_has_no_df(self, conn: SQLConnector) -> None:
        r = await conn.run_query_async("SELECT * FROM does_not_exist")
        assert not r.succeeded and r.df is None and r.error is not None


class TestRunQueryMessaging:
    def _tool(self, conn: SQLConnector) -> RunQueryTool:
        return RunQueryTool(conn, timeout=10)

    @pytest.mark.asyncio
    async def test_dml_reports_affected(self, conn: SQLConnector) -> None:
        tool = self._tool(conn)
        await tool("CREATE TABLE t(id INT, v INT)")
        await tool("INSERT INTO t VALUES (1,1),(2,2),(3,3)")

        assert "2 rows affected" in await tool("UPDATE t SET v=9 WHERE id<=2")
        assert "1 row affected" in await tool("DELETE FROM t WHERE id=3")

    @pytest.mark.asyncio
    async def test_zero_affected_nudges_where_clause(self, conn: SQLConnector) -> None:
        tool = self._tool(conn)
        await tool("CREATE TABLE t(id INT, v INT)")
        await tool("INSERT INTO t VALUES (1,1)")
        msg = await tool("UPDATE t SET v=9 WHERE id=999")
        assert "0 rows were affected" in msg and "WHERE" in msg

    @pytest.mark.asyncio
    async def test_ddl_plain_success(self, conn: SQLConnector) -> None:
        msg = await self._tool(conn)("CREATE TABLE t(id INT)")
        assert msg.startswith("(statement executed successfully)")
        assert "affected" not in msg  # plain DDL success carries no row-count clause


def _ctx() -> Any:
    return SimpleNamespace(tool_call_id="c")


def _emit_const(value: object) -> Callable[[list[ModelMessage], AgentInfo], ModelResponse]:
    """Stub subagent: call ``submit_answer`` with every output field set to ``value``."""

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        emit = next(t for t in info.output_tools if t.name == "submit_answer")
        fields = list((emit.parameters_json_schema.get("properties") or {}).keys())
        return ModelResponse(parts=[ToolCallPart(tool_name="submit_answer", args={f: value for f in fields})])

    return fn


class TestSubagentZeroMatchGuard:
    @pytest.mark.asyncio
    async def test_nanosecond_timestamp_key_zero_match_is_reported(self, conn: SQLConnector) -> None:
        # A nanosecond-precision timestamp key round-trips through pandas as a
        # microsecond value, so the write-back WHERE matches 0 rows. This is a
        # silent no-op that no key-validation can catch — affected_rows == 0 is
        # what surfaces it.
        await conn.run_query_async("CREATE TABLE t(k TIMESTAMP_NS, label VARCHAR)")
        await conn.run_query_async(
            "INSERT INTO t VALUES (TIMESTAMP_NS '2024-01-01 00:00:00.123456789', NULL),"
            "(TIMESTAMP_NS '2024-06-01 12:00:00.987654321', NULL)"
        )
        tool = RunSubagentForEachRowTool(conn, subagent_llm=FunctionModel(_emit_const("X")), store_metadata=True)
        summary = await tool.__call__(
            _ctx(),
            None,
            "t",
            task_query="SELECT * FROM t",
            task_instruction="x",
            key_columns=["k"],
            output_columns=["label"],
        )
        assert "failed for 2 rows" in summary
        assert "write matched 0 rows" in summary
        rows = await conn.run_query_async("SELECT label FROM t")
        assert rows.df is not None
        assert all(r["label"] is None for r in rows.df.to_dict("records"))
