import asyncio

import pytest
import tempfile
import sqlalchemy
import os
from typing import AsyncGenerator, Any
from tabulaflow.toolhub.run_query import RunQueryTool, LLMParameter, _format_latency
from tabulaflow.core.db_connector.sql_conn import SQLConnector, _contains_ddl_statement, _contains_write_statement
from sqlalchemy.ext.asyncio import create_async_engine

INIT_SQL = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100), age INTEGER);",
    "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL, FOREIGN KEY (user_id) REFERENCES users(id));",
    "INSERT INTO users (id, name, age) VALUES (1, 'Alice', 25), (2, 'Bob', 30), (3, 'Charlie', NULL);",
    "INSERT INTO orders (id, user_id, amount) VALUES (1, 1, 100.0), (2, 1, 150.5), (3, 2, 200.0), (4, 2, 75.25);",
]


@pytest.fixture
async def sql_engine() -> AsyncGenerator[Any, None]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            for sql in INIT_SQL:
                await conn.execute(sqlalchemy.text(sql))
        yield engine
        if os.path.exists(db_path):
            os.unlink(db_path)
        await engine.dispose()


@pytest.fixture
async def db_connector(sql_engine: Any) -> SQLConnector:
    return await SQLConnector.from_url_async(
        global_id="test_sqlite",
        url=sql_engine.url,
        db_name="test_db",
        # Disable the on-disk schema cache: it is keyed by ``global_id`` and would
        # otherwise leak a ``widgets`` table created by one run into the next.
        enable_schema_caching=False,
    )


@pytest.mark.asyncio
async def test_run_query_successful(db_connector: SQLConnector) -> None:
    """Test a successful query execution."""
    tool = RunQueryTool(db_connector, enable_params=True, timeout=10)
    result: str = await tool("SELECT * FROM users ORDER BY id")

    assert "(warning:" not in result.lower()
    assert "(query failed:" not in result.lower()
    assert "Alice" in result
    assert "Bob" in result
    assert "Charlie" in result
    assert tool.metrics().num_calls == 1
    assert tool.metrics().error_query_failed == 0
    assert tool.metrics().error_timeout == 0


def test_format_latency() -> None:
    assert _format_latency(None) == ""
    assert _format_latency(0.23) == "230ms"
    assert _format_latency(0.0009) == "1ms"
    assert _format_latency(1.5) == "1.50s"
    assert _format_latency(12.345) == "12.35s"


@pytest.mark.asyncio
async def test_run_query_reports_latency(db_connector: SQLConnector) -> None:
    """A successful query surfaces the connector-measured latency in its response."""
    tool = RunQueryTool(db_connector, enable_params=True, timeout=10)
    result: str = await tool("SELECT * FROM users ORDER BY id")
    assert "(latency:" in result


@pytest.mark.asyncio
async def test_run_query_with_parameters(db_connector: SQLConnector) -> None:
    """Test query execution with parameters."""
    tool = RunQueryTool(db_connector, enable_params=True, timeout=10)
    result: str = await tool(
        "SELECT * FROM users WHERE age > :min_age ORDER BY id",
        parameters=[LLMParameter(parameter_name="min_age", parameter_value=25)],
    )

    assert "Bob" in result
    assert "Alice" not in result  # Alice has age 25, not > 25
    assert tool.metrics().num_calls == 1


@pytest.mark.asyncio
async def test_run_query_empty_result(db_connector: SQLConnector) -> None:
    """Test query that returns empty results."""
    tool = RunQueryTool(db_connector, enable_params=True, timeout=10)
    result: str = await tool("SELECT * FROM users WHERE age > 100")

    assert "query executed successfully, but results are empty" in result
    assert tool.metrics().num_calls == 1


@pytest.mark.asyncio
async def test_run_query_ddl_statement_success(db_connector: SQLConnector) -> None:
    """A non-row-returning statement (DDL) reports success, not empty results."""
    db_connector.read_only = False
    tool = RunQueryTool(db_connector, enable_params=True, timeout=10)
    result: str = await tool("CREATE TABLE doohickeys (id INTEGER PRIMARY KEY)")

    assert "statement executed successfully" in result
    assert "results are empty" not in result


@pytest.mark.asyncio
async def test_run_query_with_null_column(db_connector: SQLConnector) -> None:
    """Test query that returns a column with all null values."""
    tool = RunQueryTool(db_connector, enable_params=True, timeout=10)
    result: str = await tool("SELECT NULL as all_null FROM users")

    assert "all_null" in result
    assert "[NULL]" in result
    assert tool.metrics().num_calls == 1


@pytest.mark.asyncio
async def test_run_query_failed(db_connector: SQLConnector) -> None:
    """Test query that fails due to SQL error."""
    tool = RunQueryTool(db_connector, enable_params=True, timeout=10)
    result: str = await tool("SELECT * FROM nonexistent_table")

    # print(result)

    assert "query failed:" in result
    assert "[SQL" not in result
    assert "(Background on this error" not in result
    assert tool.metrics().num_calls == 1
    assert tool.metrics().error_query_failed == 1


@pytest.mark.asyncio
async def test_run_query_timeout(db_connector: SQLConnector) -> None:
    """Test query timeout."""
    tool = RunQueryTool(db_connector, enable_params=True, timeout=1)

    # Create a query that takes a long time
    # For SQLite, we can simulate a long query by doing many cross joins
    result: str = await tool(
        """
        WITH RECURSIVE cnt(x) AS (
            SELECT 1
            UNION ALL
            SELECT x+1 FROM cnt
            LIMIT 10000000
        )
        SELECT COUNT(*) FROM cnt
        """
    )

    # The query should timeout
    assert "query timed out" in result or "query failed:" in result
    assert tool.metrics().error_timeout == 1
    assert tool.metrics().error_query_failed == 0
    assert tool.metrics().num_calls == 1


@pytest.mark.parametrize(
    "query, expected",
    [
        ("ALTER TABLE t ADD COLUMN c TEXT", True),
        ("CREATE TABLE t (id INT)", True),
        ("DROP TABLE t", True),
        ("TRUNCATE TABLE t", True),
        ("RENAME TABLE t TO t2", True),
        ("  -- comment\n  ALTER TABLE t ADD COLUMN c TEXT", True),
        ("SELECT 1", False),
        ("INSERT INTO t VALUES (1)", False),
        ("UPDATE t SET x = 1", False),
        ("DELETE FROM t WHERE id = 1", False),
        # Multi-statement: DDL in second statement
        ("SELECT 1; ALTER TABLE t ADD COLUMN c TEXT", True),
    ],
)
def test_contains_ddl_statement(query: str, expected: bool) -> None:
    assert _contains_ddl_statement(query) == expected


@pytest.mark.parametrize(
    "query, expected",
    [
        # Read-only — no match
        ("SELECT 1", None),
        ("SELECT * FROM t WHERE id = 1", None),
        ("WITH cte AS (SELECT 1) SELECT * FROM cte", None),
        ("", None),
        ("   ", None),
        ("-- just a comment", None),
        # DML
        ("INSERT INTO t VALUES (1)", "INSERT"),
        ("UPDATE t SET x = 1", "UPDATE"),
        ("DELETE FROM t WHERE id = 1", "DELETE"),
        ("MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE SET x = s.x", "MERGE"),
        # DDL
        ("CREATE TABLE t (a INT)", "CREATE"),
        ("ALTER TABLE t ADD COLUMN c TEXT", "ALTER"),
        ("DROP TABLE t", "DROP"),
        ("TRUNCATE TABLE t", "TRUNCATE"),
        # DCL
        ("GRANT SELECT ON t TO u", "GRANT"),
        ("REVOKE SELECT ON t FROM u", "REVOKE"),
        # Stored procs
        ("CALL my_proc()", "CALL"),
        ("EXEC sp_who", "EXEC"),
        # Bulk / file ops (Snowflake et al.)
        ("COPY t FROM 's3://b/k'", "COPY"),
        ("LOAD DATA INFILE 'f.csv' INTO TABLE t", "LOAD"),
        ("UNLOAD ('SELECT * FROM t') TO 's3://b/k'", "UNLOAD"),
        # Database attachment
        ("ATTACH 'other.duckdb' AS other", "ATTACH"),
        ("DETACH other", "DETACH"),
        # Comments before keyword
        ("  -- read-only check\n  INSERT INTO t VALUES (1)", "INSERT"),
        ("/* block */ DELETE FROM t", "DELETE"),
        ("-- one\n-- two\nUPDATE t SET x = 1", "UPDATE"),
        # Multi-statement: write in second statement
        ("SELECT 1; INSERT INTO t VALUES (1)", "INSERT"),
        ("SELECT 1; SELECT 2", None),
        # EXECUTE IMMEDIATE: opaque dynamic SQL — explicitly NOT treated as a write
        ("EXECUTE IMMEDIATE 'INSERT INTO t VALUES (1)'", None),
        ("EXECUTE IMMEDIATE 'SELECT 1'", None),
        # Bare EXECUTE (without IMMEDIATE) — treated as write (stored proc invocation)
        ("EXECUTE my_proc", "EXECUTE"),
    ],
)
def test_contains_write_statement(query: str, expected: str | None) -> None:
    assert _contains_write_statement(query) == expected


@pytest.mark.asyncio
async def test_run_query_refresh_updates_schema(db_connector: SQLConnector) -> None:
    """DDL via run_query with refresh=True should update the connector's cached schema."""
    db_connector.read_only = False
    tool = RunQueryTool(db_connector, enable_params=True, enable_refresh=True, timeout=10)

    table_names_before = {t.name for t in db_connector.schema.tables}
    assert "widgets" not in table_names_before

    # Without refresh: schema is stale.
    await tool("CREATE TABLE widgets (id INTEGER PRIMARY KEY, name TEXT)", refresh=False)
    assert "widgets" not in {t.name for t in db_connector.schema.tables}

    # With refresh: schema reflects the new table.
    result = await tool("CREATE TABLE gadgets (id INTEGER PRIMARY KEY, label TEXT)", refresh=True)
    assert "schema refreshed" in result
    table_names_after = {t.name for t in db_connector.schema.tables}
    assert "widgets" in table_names_after
    assert "gadgets" in table_names_after


@pytest.mark.asyncio
async def test_run_query_refresh_disabled_ignores_flag(db_connector: SQLConnector) -> None:
    """When enable_refresh=False, refresh=True passed to __call__ is ignored."""
    db_connector.read_only = False
    tool = RunQueryTool(db_connector, enable_params=True, enable_refresh=False, timeout=10)

    result = await tool("CREATE TABLE thingamajigs (id INTEGER PRIMARY KEY)", refresh=True)
    assert "schema refreshed" not in result
    assert "thingamajigs" not in {t.name for t in db_connector.schema.tables}


def test_run_query_pydantic_tool_signatures() -> None:
    """as_pydantic_ai_tool should select the variant matching the enabled flags."""
    import inspect

    from tabulaflow.toolhub.run_query import RunQueryTool

    class _StubConnector:
        connector_type = "sql"
        global_id = "stub"

    stub: Any = _StubConnector()

    matrix = [
        (False, False, {"query"}),
        (True, False, {"query", "parameters"}),
        (False, True, {"query", "refresh"}),
        (True, True, {"query", "parameters", "refresh"}),
    ]
    for enable_params, enable_refresh, expected in matrix:
        tool = RunQueryTool(stub, enable_params=enable_params, enable_refresh=enable_refresh, timeout=None)
        fn = tool.as_pydantic_ai_tool().function
        params = set(inspect.signature(fn).parameters) - {"self"}
        assert params == expected, (enable_params, enable_refresh, params)


@pytest.mark.asyncio
async def test_concurrent_ddl_serialized(db_connector: SQLConnector) -> None:
    """Concurrent ALTER TABLE statements should succeed thanks to DDL lock."""
    db_connector.read_only = False

    async def alter(col: str) -> None:
        await db_connector.run_query_async(f"ALTER TABLE users ADD COLUMN {col} TEXT")

    results = await asyncio.gather(alter("extra_a"), alter("extra_b"), return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    assert errors == [], f"Concurrent ALTER failed: {errors}"
