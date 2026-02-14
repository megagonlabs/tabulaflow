import pytest
import tempfile
import sqlalchemy
import os
from typing import AsyncGenerator, Any
import pandas as pd
from mintq.utils import extract_all_source_columns
from mintq.db_connector.sql_conn import SQLConnector
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema
from sqlalchemy.ext.asyncio import create_async_engine


def _make_col(name: str, dtype: str = "VARCHAR") -> SQLColumnSchema:
    """Helper to create a minimal SQLColumnSchema for testing."""
    return SQLColumnSchema(
        name=name, dtype=dtype, nullable=True, null_ratio=0.0,
        num_unique=None, unique_ratio=None, examples=[],
    )


def _make_table(
    name: str, columns: list[str], schema_name: str | None = None, dtypes: list[str] | None = None,
) -> SQLTableSchema:
    """Helper to create a minimal SQLTableSchema for testing."""
    if dtypes is None:
        dtypes = ["VARCHAR"] * len(columns)
    return SQLTableSchema(
        name=name, schema_name=schema_name, is_view=False,
        columns=[_make_col(c, d) for c, d in zip(columns, dtypes)],
        primary_key=[], num_rows=0, foreign_keys=[], sampled_df=pd.DataFrame(),
    )

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


def test_union_all_query() -> None:
    """Test extracting columns from a UNION ALL query."""
    query = """
    SELECT name FROM users WHERE id = 1
    UNION ALL
    SELECT name FROM users WHERE id = 2
    """
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "name"), ("users", "id")}


def test_union_all_different_tables() -> None:
    """Test extracting columns from UNION ALL with different tables."""
    query = """
    SELECT user_id, amount FROM orders WHERE amount > 100
    UNION ALL
    SELECT id, age FROM users WHERE age > 20
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("orders", "user_id"),
        ("orders", "amount"),
        ("users", "id"),
        ("users", "age"),
    }


def test_intersect_query() -> None:
    """Test extracting columns from an INTERSECT query."""
    query = """
    SELECT name FROM users WHERE age > 20
    INTERSECT
    SELECT name FROM users WHERE id < 10
    """
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "name"), ("users", "age"), ("users", "id")}


def test_except_query() -> None:
    """Test extracting columns from an EXCEPT query."""
    query = """
    SELECT id FROM users
    EXCEPT
    SELECT user_id FROM orders
    """
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "id"), ("orders", "user_id")}


def test_subquery_in_where() -> None:
    """Test extracting columns from subquery in WHERE clause."""
    query = """
    SELECT name FROM users
    WHERE id = (SELECT user_id FROM orders WHERE amount = (SELECT MAX(amount) FROM orders))
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("orders", "user_id"),
        ("orders", "amount"),
    }


def test_subquery_in_select() -> None:
    """Test extracting columns from subquery in SELECT clause."""
    query = """
    SELECT u.name, (SELECT MAX(o.amount) FROM orders o WHERE o.user_id = u.id) as max_order
    FROM users u
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("orders", "amount"),
        ("orders", "user_id"),
    }


def test_exists_subquery() -> None:
    """Test extracting columns from EXISTS subquery."""
    query = """
    SELECT name FROM users u
    WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.amount > 100)
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("orders", "user_id"),
        ("orders", "amount"),
    }


def test_in_subquery() -> None:
    """Test extracting columns from IN subquery."""
    query = """
    SELECT name FROM users
    WHERE id IN (SELECT user_id FROM orders WHERE amount > 50)
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("orders", "user_id"),
        ("orders", "amount"),
    }


def test_case_when_expression() -> None:
    """Test extracting columns from CASE WHEN expression."""
    query = """
    SELECT
        name,
        CASE
            WHEN age > 30 THEN 'senior'
            WHEN age > 20 THEN 'adult'
            ELSE 'young'
        END as category
    FROM users
    """
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "name"), ("users", "age")}


def test_window_function() -> None:
    """Test extracting columns from window functions."""
    query = """
    SELECT
        user_id,
        amount,
        SUM(amount) OVER (PARTITION BY user_id ORDER BY id) as running_total
    FROM orders
    """
    result = extract_all_source_columns(query)

    assert set(result) == {("orders", "user_id"), ("orders", "amount"), ("orders", "id")}


def test_nested_subqueries() -> None:
    """Test extracting columns from deeply nested subqueries."""
    query = """
    SELECT name FROM users
    WHERE id = (
        SELECT user_id FROM orders
        WHERE amount = (
            SELECT MAX(amount) FROM orders
            WHERE user_id IN (SELECT id FROM users WHERE age > 25)
        )
    )
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("users", "age"),
        ("orders", "user_id"),
        ("orders", "amount"),
    }


def test_complex_union_with_subqueries() -> None:
    """Test extracting columns from UNION ALL with subqueries (like the original bug case)."""
    query = """
    SELECT name FROM users
    WHERE id = (SELECT user_id FROM orders ORDER BY amount DESC LIMIT 1)
    UNION ALL
    SELECT name FROM users
    WHERE age = (SELECT MAX(age) FROM users)
    """
    result = extract_all_source_columns(query)

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("users", "age"),
        ("orders", "user_id"),
        ("orders", "amount"),
    }


def test_multiple_unions() -> None:
    """Test extracting columns from multiple UNION ALL clauses."""
    query = """
    SELECT id, name FROM users WHERE age > 30
    UNION ALL
    SELECT id, name FROM users WHERE age > 20
    UNION ALL
    SELECT id, name FROM users WHERE age > 10
    """
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "id"), ("users", "name"), ("users", "age")}


# --------------------------------------------------------------------------- #
#  Snowflake dialect + schema_name tests                                       #
# --------------------------------------------------------------------------- #

@pytest.fixture
def snowflake_schema() -> SQLSchema:
    """Schema mimicking Snowflake AIRLINES database with schema_name='airlines'."""
    return SQLSchema(
        name="AIRLINES",
        tables=[
            _make_table("airports_data", ["airport_code", "airport_name", "city", "coordinates", "timezone"], schema_name="airlines"),
            _make_table("flights", ["flight_id", "flight_no", "scheduled_departure", "scheduled_arrival", "departure_airport", "arrival_airport", "status", "aircraft_code", "actual_departure", "actual_arrival"], schema_name="airlines"),
        ],
    )


def test_snowflake_simple_with_schema_name(snowflake_schema: SQLSchema) -> None:
    """Test Snowflake query with schema-qualified table (airlines.airports_data) and schema passed."""
    query = 'SELECT a.airport_code, a.city FROM airlines.airports_data a WHERE a.timezone IS NOT NULL'
    result = extract_all_source_columns(query, schema=snowflake_schema, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "AIRPORT_CODE"),
        ("AIRPORTS_DATA", "CITY"),
        ("AIRPORTS_DATA", "TIMEZONE"),
    }


def test_snowflake_quoted_lowercase_fallback(snowflake_schema: SQLSchema) -> None:
    """Test that quoted lowercase identifiers (Snowflake case-sensitive) fall back gracefully.

    Snowflake quoted identifiers ("airport_code") stay lowercase, but MappingSchema
    normalizes to UPPERCASE. qualify() can't match them, so we fall back to schema-less
    qualify which still extracts columns correctly.
    """
    query = '''
    SELECT a."airport_code", a."city"
    FROM airlines.airports_data a
    WHERE a."timezone" IS NOT NULL
    '''
    result = extract_all_source_columns(query, schema=snowflake_schema, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "airport_code"),
        ("AIRPORTS_DATA", "city"),
        ("AIRPORTS_DATA", "timezone"),
    }


def test_snowflake_quoted_lowercase_without_schema() -> None:
    """Test that quoted lowercase Snowflake identifiers work without schema too."""
    query = '''
    SELECT a."airport_code", a."city"
    FROM airlines.airports_data a
    WHERE a."timezone" IS NOT NULL
    '''
    result = extract_all_source_columns(query, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "airport_code"),
        ("AIRPORTS_DATA", "city"),
        ("AIRPORTS_DATA", "timezone"),
    }


def test_snowflake_cte_with_schema(snowflake_schema: SQLSchema) -> None:
    """Test Snowflake CTE query with schema — verifies qualify fallback on multi-CTE."""
    query = """
    WITH recent_flights AS (
        SELECT f.departure_airport, f.arrival_airport
        FROM airlines.flights f
        WHERE f.status = 'Arrived'
    )
    SELECT rf.departure_airport
    FROM recent_flights rf
    """
    result = extract_all_source_columns(query, schema=snowflake_schema, language="snowflake")

    assert set(result) == {
        ("FLIGHTS", "DEPARTURE_AIRPORT"),
        ("FLIGHTS", "ARRIVAL_AIRPORT"),
        ("FLIGHTS", "STATUS"),
    }


def test_snowflake_multi_cte_join_with_schema(snowflake_schema: SQLSchema) -> None:
    """Test Snowflake multi-CTE with JOIN between CTE and real table, with schema passed."""
    query = """
    WITH airport_cities AS (
        SELECT a.airport_code, a.city
        FROM airlines.airports_data a
    )
    SELECT f.flight_no, ac.city
    FROM airlines.flights f
    JOIN airport_cities ac ON ac.airport_code = f.departure_airport
    """
    result = extract_all_source_columns(query, schema=snowflake_schema, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "AIRPORT_CODE"),
        ("AIRPORTS_DATA", "CITY"),
        ("FLIGHTS", "FLIGHT_NO"),
        ("FLIGHTS", "DEPARTURE_AIRPORT"),
    }


def test_snowflake_complex_multi_cte_with_schema(snowflake_schema: SQLSchema) -> None:
    """Test the full AIRLINES haversine-distance query with schema — the original bug case."""
    query = '''WITH abakan_airport AS (
      SELECT "airport_code"
      FROM airlines.airports_data
      WHERE LOWER(TRY_PARSE_JSON("city"):en::STRING) = 'abakan'
    ),
    city_coordinates AS (
      SELECT
        a."airport_code",
        LOWER(TRY_PARSE_JSON(a."city"):en::STRING) AS city_en,
        SPLIT(TRANSLATE(a."coordinates", '()', ''), ',') AS coord_array
      FROM airlines.airports_data a
    ),
    flight_routes AS (
      SELECT
        f."departure_airport",
        dep.city_en AS city1,
        dep.coord_array AS coord1,
        f."arrival_airport",
        arr.city_en AS city2,
        arr.coord_array AS coord2
      FROM airlines.flights f
      JOIN city_coordinates dep ON dep."airport_code" = f."departure_airport"
      JOIN city_coordinates arr ON arr."airport_code" = f."arrival_airport"
      WHERE f."departure_airport" IN (SELECT "airport_code" FROM abakan_airport)
         OR f."arrival_airport" IN (SELECT "airport_code" FROM abakan_airport)
    ),
    route_distances AS (
      SELECT
        LEAST(city1, city2) AS ordered_city1,
        GREATEST(city1, city2) AS ordered_city2,
        coord1,
        coord2,
        2 * 6371 * ASIN(SQRT(
          POWER(SIN((CAST(coord2[1] AS FLOAT) * PI()/180 - CAST(coord1[1] AS FLOAT) * PI()/180) / 2), 2)
          + COS(CAST(coord1[1] AS FLOAT) * PI()/180) * COS(CAST(coord2[1] AS FLOAT) * PI()/180)
          * POWER(SIN((CAST(coord2[0] AS FLOAT) * PI()/180 - CAST(coord1[0] AS FLOAT) * PI()/180) / 2), 2)
        )) AS distance_km
      FROM flight_routes
    )
    SELECT MAX(distance_km) AS longest_route_km
    FROM route_distances'''

    # With schema — previously returned [] due to qualify crash
    result_with = extract_all_source_columns(query, schema=snowflake_schema, language="snowflake")
    assert set(result_with) == {
        ("AIRPORTS_DATA", "airport_code"),
        ("AIRPORTS_DATA", "city"),
        ("AIRPORTS_DATA", "coordinates"),
        ("FLIGHTS", "departure_airport"),
        ("FLIGHTS", "arrival_airport"),
    }

    # Without schema — should give the same result
    result_without = extract_all_source_columns(query, language="snowflake")
    assert set(result_with) == set(result_without)


def test_snowflake_schema_with_unquoted_identifiers(snowflake_schema: SQLSchema) -> None:
    """Test that unquoted Snowflake identifiers (normalized to UPPERCASE) work with schema."""
    query = """
    SELECT airport_code, city
    FROM airlines.airports_data
    WHERE timezone IS NOT NULL
    """
    result = extract_all_source_columns(query, schema=snowflake_schema, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "AIRPORT_CODE"),
        ("AIRPORTS_DATA", "CITY"),
        ("AIRPORTS_DATA", "TIMEZONE"),
    }


def test_snowflake_subquery_in_where_with_schema(snowflake_schema: SQLSchema) -> None:
    """Test Snowflake subquery in WHERE clause with schema — verifies CTE + subquery combo."""
    query = """
    SELECT f.flight_no, f.departure_airport
    FROM airlines.flights f
    WHERE f.departure_airport IN (
        SELECT a.airport_code FROM airlines.airports_data a WHERE a.city = 'Moscow'
    )
    """
    result = extract_all_source_columns(query, schema=snowflake_schema, language="snowflake")

    assert set(result) == {
        ("FLIGHTS", "FLIGHT_NO"),
        ("FLIGHTS", "DEPARTURE_AIRPORT"),
        ("AIRPORTS_DATA", "AIRPORT_CODE"),
        ("AIRPORTS_DATA", "CITY"),
    }


def test_schema_without_schema_name_still_works() -> None:
    """Test that SQLite-style schemas (no schema_name) still work correctly with the new code."""
    schema = SQLSchema(
        name="test_db",
        tables=[
            _make_table("users", ["id", "name", "age"], dtypes=["INTEGER", "VARCHAR", "INTEGER"]),
            _make_table("orders", ["id", "user_id", "amount"], dtypes=["INTEGER", "INTEGER", "REAL"]),
        ],
    )
    query = """
    SELECT u.name, o.amount
    FROM users u
    JOIN orders o ON u.id = o.user_id
    WHERE u.age > 20
    """
    result = extract_all_source_columns(query, schema=schema, language="sqlite")

    assert set(result) == {
        ("users", "name"),
        ("users", "id"),
        ("users", "age"),
        ("orders", "amount"),
        ("orders", "user_id"),
    }
