import pytest
import tempfile
import sqlalchemy
import os
from typing import AsyncGenerator, Any
from mintq.agenthub.utils import extract_all_source_columns
from mintq.db_connector.sql_conn import SQLConnector
from mintq.schema import SQLSchema
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
        db_name="test_db",
        engine_type="async",
        url=sql_engine.url,
    )


@pytest.fixture
async def schema(db_connector: SQLConnector) -> SQLSchema:
    return db_connector.schema


def test_simple_query_without_schema() -> None:
    """Test extracting columns from a simple query without schema."""
    query = "SELECT name, age FROM users WHERE id = 1"
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "name"), ("users", "age"), ("users", "id")}


def test_query_with_table_alias_without_schema() -> None:
    """Test extracting columns with table aliases."""
    query = "SELECT u.name, u.age FROM users u WHERE u.id = 1"
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "name"), ("users", "age"), ("users", "id")}


def test_join_query_without_schema() -> None:
    """Test extracting columns from a JOIN query."""
    query = """
    SELECT u.name, o.amount
    FROM users u
    JOIN orders o ON u.id = o.user_id
    WHERE u.age > 20
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("users", "age"),
        ("orders", "amount"),
        ("orders", "user_id"),
    }


def test_cte_query_without_schema() -> None:
    """Test extracting columns from a CTE query, tracing back to source tables."""
    query = """
    WITH user_orders AS (
        SELECT u.id, u.name, o.amount
        FROM users u
        JOIN orders o ON u.id = o.user_id
    )
    SELECT uo.name, uo.amount
    FROM user_orders uo
    WHERE uo.id > 0
    """
    result = extract_all_source_columns(query)

    # All columns should trace back to source tables (users, orders), not the CTE
    assert set(result) == {
        ("users", "id"),
        ("users", "name"),
        ("orders", "amount"),
        ("orders", "user_id"),
    }


def test_subquery_without_schema() -> None:
    """Test extracting columns from a subquery in FROM clause."""
    query = """
    SELECT t.total_amount
    FROM (
        SELECT user_id, SUM(amount) as total_amount
        FROM orders
        GROUP BY user_id
    ) t
    WHERE t.user_id > 0
    """
    result = extract_all_source_columns(query)

    assert set(result) == {("orders", "user_id"), ("orders", "amount")}


def test_invalid_sql_returns_empty() -> None:
    """Test that invalid SQL returns an empty list."""
    result = extract_all_source_columns("NOT VALID SQL AT ALL")
    assert result == []


def test_empty_query_returns_empty() -> None:
    """Test that empty query returns an empty list."""
    result = extract_all_source_columns("")
    assert result == []


@pytest.mark.asyncio
async def test_select_star_with_schema(schema: SQLSchema) -> None:
    """Test that SELECT * is expanded when schema is provided."""
    query = "SELECT * FROM users"
    result = extract_all_source_columns(query, schema)

    # Should include all columns from users table
    assert set(result) == {("users", "id"), ("users", "name"), ("users", "age")}


@pytest.mark.asyncio
async def test_select_star_without_schema() -> None:
    """Test that SELECT * returns empty when no schema is provided."""
    query = "SELECT * FROM users"
    result = extract_all_source_columns(query)

    # Without schema, cannot expand SELECT *
    assert result == []


@pytest.mark.asyncio
async def test_select_table_star_with_schema(schema: SQLSchema) -> None:
    """Test that SELECT table.* is expanded when schema is provided."""
    query = """
    SELECT u.*, o.amount
    FROM users u
    JOIN orders o ON u.id = o.user_id
    """
    result = extract_all_source_columns(query, schema)

    # Should include all columns from users (via u.*) plus orders columns
    assert set(result) == {
        ("users", "id"),
        ("users", "name"),
        ("users", "age"),
        ("orders", "amount"),
        ("orders", "user_id"),
    }


@pytest.mark.asyncio
async def test_complex_query_with_schema(schema: SQLSchema) -> None:
    """Test a complex query with CTE, JOIN, and ORDER BY."""
    query = """
    WITH high_value_orders AS (
        SELECT o.user_id, o.amount
        FROM orders o
        WHERE o.amount > 100
    )
    SELECT u.name, hvo.amount
    FROM users u
    JOIN high_value_orders hvo ON u.id = hvo.user_id
    ORDER BY u.age DESC
    """
    result = extract_all_source_columns(query, schema)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("users", "age"),
        ("orders", "user_id"),
        ("orders", "amount"),
    }


@pytest.mark.asyncio
async def test_group_by_having_with_schema(schema: SQLSchema) -> None:
    """Test extracting columns from GROUP BY and HAVING clauses."""
    query = """
    SELECT user_id, SUM(amount) as total
    FROM orders
    GROUP BY user_id
    HAVING SUM(amount) > 100
    """
    result = extract_all_source_columns(query, schema)

    assert set(result) == {("orders", "user_id"), ("orders", "amount")}
