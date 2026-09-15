from tabulaflow.research.query_analysis import extract_all_source_columns, sqlglot_dialect


def test_postgresql_language_maps_to_sqlglot_postgres_dialect() -> None:
    assert sqlglot_dialect("postgresql") == "postgres"


def test_simple_query() -> None:
    """Test extracting columns from a simple query."""
    query = "SELECT name, age FROM users WHERE id = 1"
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "name"), ("users", "age"), ("users", "id")}


def test_query_with_table_alias() -> None:
    """Test extracting columns with table aliases."""
    query = "SELECT u.name, u.age FROM users u WHERE u.id = 1"
    result = extract_all_source_columns(query)

    assert set(result) == {("users", "name"), ("users", "age"), ("users", "id")}


def test_join_query() -> None:
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


def test_cte_query() -> None:
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


def test_subquery() -> None:
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


def test_select_star_returns_empty() -> None:
    """Test that SELECT * returns empty (cannot expand without schema)."""
    result = extract_all_source_columns("SELECT * FROM users")
    assert result == []


def test_group_by_having() -> None:
    """Test extracting columns from GROUP BY and HAVING clauses."""
    query = """
    SELECT user_id, SUM(amount) as total
    FROM orders
    GROUP BY user_id
    HAVING SUM(amount) > 100
    """
    result = extract_all_source_columns(query)

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
#  Snowflake dialect tests                                                     #
# --------------------------------------------------------------------------- #


def test_snowflake_schema_qualified_table() -> None:
    """Test Snowflake query with schema-qualified table (airlines.airports_data)."""
    query = "SELECT a.airport_code, a.city FROM airlines.airports_data a WHERE a.timezone IS NOT NULL"
    result = extract_all_source_columns(query, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "AIRPORT_CODE"),
        ("AIRPORTS_DATA", "CITY"),
        ("AIRPORTS_DATA", "TIMEZONE"),
    }


def test_snowflake_quoted_lowercase_identifiers() -> None:
    """Test Snowflake quoted lowercase identifiers (case-sensitive, preserved as-is)."""
    query = """
    SELECT a."airport_code", a."city"
    FROM airlines.airports_data a
    WHERE a."timezone" IS NOT NULL
    """
    result = extract_all_source_columns(query, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "airport_code"),
        ("AIRPORTS_DATA", "city"),
        ("AIRPORTS_DATA", "timezone"),
    }


def test_snowflake_cte() -> None:
    """Test Snowflake CTE query."""
    query = """
    WITH recent_flights AS (
        SELECT f.departure_airport, f.arrival_airport
        FROM airlines.flights f
        WHERE f.status = 'Arrived'
    )
    SELECT rf.departure_airport
    FROM recent_flights rf
    """
    result = extract_all_source_columns(query, language="snowflake")

    assert set(result) == {
        ("FLIGHTS", "DEPARTURE_AIRPORT"),
        ("FLIGHTS", "ARRIVAL_AIRPORT"),
        ("FLIGHTS", "STATUS"),
    }


def test_snowflake_multi_cte_join() -> None:
    """Test Snowflake multi-CTE with JOIN between CTE and real table."""
    query = """
    WITH airport_cities AS (
        SELECT a.airport_code, a.city
        FROM airlines.airports_data a
    )
    SELECT f.flight_no, ac.city
    FROM airlines.flights f
    JOIN airport_cities ac ON ac.airport_code = f.departure_airport
    """
    result = extract_all_source_columns(query, language="snowflake")

    assert set(result) == {
        ("AIRPORTS_DATA", "AIRPORT_CODE"),
        ("AIRPORTS_DATA", "CITY"),
        ("FLIGHTS", "FLIGHT_NO"),
        ("FLIGHTS", "DEPARTURE_AIRPORT"),
    }


def test_snowflake_complex_multi_cte() -> None:
    """Test a complex Snowflake query with 4 CTEs, JOINs, subqueries, and haversine math."""
    query = """WITH abakan_airport AS (
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
    FROM route_distances"""

    result = extract_all_source_columns(query, language="snowflake")
    assert set(result) == {
        ("AIRPORTS_DATA", "airport_code"),
        ("AIRPORTS_DATA", "city"),
        ("AIRPORTS_DATA", "coordinates"),
        ("FLIGHTS", "departure_airport"),
        ("FLIGHTS", "arrival_airport"),
    }


def test_snowflake_subquery_in_where() -> None:
    """Test Snowflake subquery in WHERE clause."""
    query = """
    SELECT f.flight_no, f.departure_airport
    FROM airlines.flights f
    WHERE f.departure_airport IN (
        SELECT a.airport_code FROM airlines.airports_data a WHERE a.city = 'Moscow'
    )
    """
    result = extract_all_source_columns(query, language="snowflake")

    assert set(result) == {
        ("FLIGHTS", "FLIGHT_NO"),
        ("FLIGHTS", "DEPARTURE_AIRPORT"),
        ("AIRPORTS_DATA", "AIRPORT_CODE"),
        ("AIRPORTS_DATA", "CITY"),
    }


def test_snowflake_trim_both_parse_fallback() -> None:
    """Test that TRIM(BOTH '(' FROM ...) which fails Snowflake parsing falls back to permissive parse."""
    query = """WITH other_airports AS (
        SELECT a."airport_code", a."coordinates"
        FROM airlines.airports_data a
        JOIN airlines.flights f ON f."departure_airport" = a."airport_code"
    ),
    other_coords AS (
        SELECT
            oa."airport_code",
            CAST(SPLIT_PART(TRIM(BOTH '(' FROM oa."coordinates"), ',', 1) AS FLOAT) AS lon2
        FROM other_airports oa
    )
    SELECT oc."airport_code"
    FROM other_coords oc"""
    result = extract_all_source_columns(query, language="snowflake")

    # Falls back to dialect-free parsing; table names stay lowercase
    assert set(result) == {
        ("airports_data", "airport_code"),
        ("airports_data", "coordinates"),
        ("flights", "departure_airport"),
    }
