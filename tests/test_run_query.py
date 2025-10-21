import pytest
import tempfile
import sqlalchemy
import os
from mintq.toolhub.run_query import RunQueryTool
from mintq.db_connector.sql_conn import SQLConnector
from sqlalchemy.ext.asyncio import create_async_engine

SQL_INIT = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100), age INTEGER);",
    "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL, FOREIGN KEY (user_id) REFERENCES users(id));",
    "INSERT INTO users (id, name, age) VALUES (1, 'Alice', 25), (2, 'Bob', 30), (3, 'Charlie', NULL);",
    "INSERT INTO orders (id, user_id, amount) VALUES (1, 1, 100.0), (2, 1, 150.5), (3, 2, 200.0), (4, 2, 75.25);",
]


@pytest.fixture
async def sql_engine():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            for sql in SQL_INIT:
                await conn.execute(sqlalchemy.text(sql))
        yield engine
        if os.path.exists(db_path):
            os.unlink(db_path)
        await engine.dispose()


@pytest.fixture
async def db_connector(sql_engine) -> SQLConnector:
    return await SQLConnector.from_url_async(
        global_id="test_sqlite",
        db_name="test_db",
        engine_type="async",
        url=sql_engine.url,
    )


@pytest.mark.asyncio
async def test_run_query_successful(db_connector):
    """Test a successful query execution."""
    tool = RunQueryTool(db_connector, timeout=10)
    result = await tool("SELECT * FROM users ORDER BY id")

    assert "(warning:" not in result.lower()
    assert "(query failed:" not in result.lower()
    assert "Alice" in result
    assert "Bob" in result
    assert "Charlie" in result
    assert tool.metrics().num_calls == 1
    assert tool.metrics().error_query_failed == 0
    assert tool.metrics().error_timeout == 0


@pytest.mark.asyncio
async def test_run_query_with_parameters(db_connector):
    """Test query execution with parameters."""
    tool = RunQueryTool(db_connector, timeout=10)
    result = await tool(
        "SELECT * FROM users WHERE age > :min_age ORDER BY id",
        parameters={"min_age": 25},
    )

    assert "Bob" in result
    assert "Alice" not in result  # Alice has age 25, not > 25
    assert tool.metrics().num_calls == 1


@pytest.mark.asyncio
async def test_run_query_empty_result(db_connector):
    """Test query that returns empty results."""
    tool = RunQueryTool(db_connector, timeout=10)
    result = await tool("SELECT * FROM users WHERE age > 100")

    assert "warning: query executed successfully, but results are empty" in result
    assert tool.metrics().num_calls == 1


@pytest.mark.asyncio
async def test_run_query_with_null_column(db_connector):
    """Test query that returns a column with all null values."""
    tool = RunQueryTool(db_connector, timeout=10)
    result = await tool("SELECT NULL as all_null FROM users")

    assert "warning: a column is entirely null" in result
    assert tool.metrics().num_calls == 1


@pytest.mark.asyncio
async def test_run_query_failed(db_connector):
    """Test query that fails due to SQL error."""
    tool = RunQueryTool(db_connector, timeout=10)
    result = await tool("SELECT * FROM nonexistent_table")

    print(result)

    assert "query failed:" in result
    assert tool.metrics().num_calls == 1
    assert tool.metrics().error_query_failed == 1


# @pytest.mark.asyncio
# async def test_run_query_timeout(db_connector):
#     """Test query timeout."""
#     tool = RunQueryTool(db_connector, timeout=1)

#     # Create a query that takes a long time
#     # For SQLite, we can simulate a long query by doing many cross joins
#     result = await tool(
#         """
#         WITH RECURSIVE cnt(x) AS (
#             SELECT 1
#             UNION ALL
#             SELECT x+1 FROM cnt
#             LIMIT 10000000
#         )
#         SELECT COUNT(*) FROM cnt
#         """
#     )

#     # The query should timeout
#     assert "query timed out" in result or "query failed:" in result
#     assert tool.metrics().num_calls == 1
