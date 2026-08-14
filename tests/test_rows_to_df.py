"""Dtype-mapping tests for the connector read path.

Most coverage runs end-to-end through ``ThrottledEngine.execute_async``
against DuckDB — the public contract — so the tests survive refactors
of the private ``_rows_to_df`` helper and exercise real driver type
mapping (HUGEINT, DECIMAL, BLOB) rather than SQLite's loose type
affinity.

A small handful of unit tests on ``_rows_to_df`` itself cover cases
that strict-typed SQL can't naturally produce: mixed Python types in
one column, or empty input.
"""

from typing import AsyncGenerator

import pandas as pd
import pytest

from tabulaflow.data.sql import _rows_to_df, ThrottledEngine


# ---------------------------------------------------------------------------
# Integration tests via DuckDB — the public contract
# ---------------------------------------------------------------------------


@pytest.fixture
async def duckdb_eng() -> AsyncGenerator[ThrottledEngine, None]:
    eng = ThrottledEngine.from_url("duckdb:///:memory:", read_only=False)
    try:
        yield eng
    finally:
        await eng.aclose()


async def _query_df(eng: ThrottledEngine, sql: str) -> pd.DataFrame:
    """Run ``sql`` with ``return_df=True`` and narrow the result type
    to ``pd.DataFrame`` (``execute_async`` returns a union)."""
    result = (await eng.execute_async(sql, return_df=True)).result
    assert isinstance(result, pd.DataFrame)
    return result


@pytest.mark.asyncio
async def test_integer_with_null_returns_int64(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        "SELECT 1::INTEGER AS x UNION ALL SELECT 2 UNION ALL SELECT NULL ORDER BY x",
    )
    assert str(df["x"].dtype) == "Int64"
    assert df["x"].iloc[0] == 1
    assert df["x"].iloc[1] == 2
    assert df["x"].iloc[2] is pd.NA


@pytest.mark.asyncio
async def test_bigint_within_int64_range_returns_int64(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        f"SELECT {2**63 - 1}::BIGINT AS x UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "Int64"


@pytest.mark.asyncio
async def test_hugeint_overflowing_int64_stays_object(duckdb_eng: ThrottledEngine) -> None:
    """HUGEINT values outside C-long range can't be cast to ``Int64``;
    they must stay ``object`` so ``_sanitize_df_strings`` can stringify
    them downstream."""
    df = await _query_df(
        duckdb_eng,
        f"SELECT {2**100}::HUGEINT AS x UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "object"
    # Value is preserved as a Python int.
    assert df["x"].iloc[0] == 2**100


@pytest.mark.asyncio
async def test_double_with_null_returns_float64(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        "SELECT 1.5::DOUBLE AS x UNION ALL SELECT 2.5 UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "Float64"


@pytest.mark.asyncio
async def test_whole_number_doubles_stay_float64(duckdb_eng: ThrottledEngine) -> None:
    """Regression: ``convert_dtypes`` would demote a DOUBLE column whose
    values happen to all be whole numbers to ``Int64``, hiding the
    source type.  Our helper preserves the int-vs-float distinction."""
    df = await _query_df(
        duckdb_eng,
        "SELECT 1.0::DOUBLE AS x UNION ALL SELECT 2.0 UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "Float64"


@pytest.mark.asyncio
async def test_boolean_with_null_returns_boolean(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        "SELECT TRUE AS x UNION ALL SELECT FALSE UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "boolean"


@pytest.mark.asyncio
async def test_varchar_with_null_returns_string(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        "SELECT 'a'::VARCHAR AS x UNION ALL SELECT 'b' UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "string"


@pytest.mark.asyncio
async def test_decimal_stays_object(duckdb_eng: ThrottledEngine) -> None:
    """``Decimal`` has no nullable extension dtype in the numpy_nullable
    backend, so the column stays ``object`` with Python ``Decimal``
    values preserved."""
    import decimal

    df = await _query_df(
        duckdb_eng,
        "SELECT 1.50::DECIMAL(10, 2) AS x UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "object"
    assert df["x"].iloc[0] == decimal.Decimal("1.50")


@pytest.mark.asyncio
async def test_blob_stays_object(duckdb_eng: ThrottledEngine) -> None:
    """BLOB / VARBINARY columns return Python ``bytes``; no nullable
    extension dtype exists so they stay ``object``."""
    df = await _query_df(
        duckdb_eng,
        "SELECT '\\x00\\x01'::BLOB AS x UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "object"


@pytest.mark.asyncio
async def test_all_null_column_stays_object(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        "SELECT NULL::INTEGER AS x UNION ALL SELECT NULL",
    )
    assert str(df["x"].dtype) == "object"


@pytest.mark.asyncio
async def test_empty_result_set(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        "SELECT 1::INTEGER AS x WHERE FALSE",
    )
    assert len(df) == 0
    assert list(df.columns) == ["x"]


@pytest.mark.asyncio
async def test_multiple_columns_independent_inference(duckdb_eng: ThrottledEngine) -> None:
    df = await _query_df(
        duckdb_eng,
        "SELECT 1::INTEGER AS i, 1.5::DOUBLE AS f, 'a'::VARCHAR AS s, TRUE AS b "
        "UNION ALL SELECT NULL, NULL, NULL, NULL",
    )
    assert str(df["i"].dtype) == "Int64"
    assert str(df["f"].dtype) == "Float64"
    assert str(df["s"].dtype) == "string"
    assert str(df["b"].dtype) == "boolean"


# ---------------------------------------------------------------------------
# Unit tests for cases that strict-typed SQL can't naturally produce
# ---------------------------------------------------------------------------


def test_mixed_int_and_float_values_become_float64() -> None:
    """A single column with both Python ``int`` and ``float`` instances
    can arise from drivers that don't normalize NUMERIC return types.
    Hard to reproduce in strict-typed SQL — covered as a unit test."""
    df = _rows_to_df([(1,), (2.5,), (None,)], ["x"])
    assert str(df["x"].dtype) == "Float64"


def test_mixed_unrelated_types_stay_object() -> None:
    """A column containing both ``str`` and ``int`` (e.g. from a
    ``UNION`` with implicit coercion in a permissive dialect) should
    fall through to ``object`` rather than picking either side."""
    df = _rows_to_df([("a",), (1,), (None,)], ["x"])
    assert str(df["x"].dtype) == "object"


def test_empty_rows_argument_returns_empty_df() -> None:
    """Defensive: callers may pass an empty row list (e.g. a ``WHERE
    FALSE`` query whose ``fetchall`` returned nothing)."""
    df = _rows_to_df([], ["x", "y"])
    assert len(df) == 0
    assert list(df.columns) == ["x", "y"]
