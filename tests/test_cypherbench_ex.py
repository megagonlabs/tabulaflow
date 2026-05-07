"""Tests for cypherbench_ex metric."""

import json

import pandas as pd
import pytest

from mintq.metrics.cypherbench_ex import (
    _df_to_tuples,
    _normalize_cell,
    _result_eq,
    _to_hashable,
    CypherBenchEx,
)
from mintq.schema import ExecResult, GoldQuery, PredQuery, SimpleNL2QTaskOutput


# ---------------------------------------------------------------------------
# _to_hashable
# ---------------------------------------------------------------------------


def test_to_hashable_scalars() -> None:
    assert _to_hashable(1) == 1
    assert _to_hashable("a") == "a"
    assert _to_hashable(None) is None
    assert _to_hashable(True) is True


def test_to_hashable_sorts_lists() -> None:
    assert _to_hashable([3, 1, 2]) == (1, 2, 3)
    assert _to_hashable(["c", "a", "b"]) == ("a", "b", "c")


def test_to_hashable_dict() -> None:
    assert _to_hashable({"b": 2, "a": 1}) == (("a", 1), ("b", 2))


def test_to_hashable_nested() -> None:
    assert _to_hashable([[2, 1], [4, 3]]) == ((1, 2), (3, 4))


# ---------------------------------------------------------------------------
# _normalize_cell
# ---------------------------------------------------------------------------


def test_normalize_cell_none_and_nan() -> None:
    assert _normalize_cell(None) is None
    assert _normalize_cell(float("nan")) is None
    # ``pd.NA`` arrives from nullable extension dtypes (``Int64`` /
    # ``boolean`` / ``string``) produced by the connector read path —
    # must normalize to ``None`` like ``NaN`` does.
    assert _normalize_cell(pd.NA) is None


def test_normalize_cell_json_list() -> None:
    assert _normalize_cell(json.dumps([3, 1, 2])) == (1, 2, 3)


def test_normalize_cell_json_dict() -> None:
    assert _normalize_cell(json.dumps({"b": 2, "a": 1})) == (("a", 1), ("b", 2))


def test_normalize_cell_plain_string() -> None:
    assert _normalize_cell("hello") == "hello"


def test_normalize_cell_scalars() -> None:
    assert _normalize_cell(42) == 42
    assert _normalize_cell(3.14) == 3.14
    assert _normalize_cell(True) is True


# ---------------------------------------------------------------------------
# _result_eq
# ---------------------------------------------------------------------------


def test_result_eq_both_empty() -> None:
    assert _result_eq([], [], order_matters=False) is True
    assert _result_eq([], [], order_matters=True) is True


def test_result_eq_exact_match() -> None:
    rows = [("a", 1), ("b", 2)]
    assert _result_eq(rows, list(rows), order_matters=False) is True
    assert _result_eq(rows, list(rows), order_matters=True) is True


def test_result_eq_different_row_order() -> None:
    r1 = [("a", 1), ("b", 2)]
    r2 = [("b", 2), ("a", 1)]
    assert _result_eq(r1, r2, order_matters=False) is True
    assert _result_eq(r1, r2, order_matters=True) is False


def test_result_eq_column_permutation() -> None:
    r1 = [("a", 1), ("b", 2)]
    r2 = [(1, "a"), (2, "b")]
    assert _result_eq(r1, r2, order_matters=False) is True


def test_result_eq_different_lengths() -> None:
    assert _result_eq([("a",)], [("a",), ("b",)], order_matters=False) is False


def test_result_eq_different_col_count() -> None:
    assert _result_eq([("a", 1)], [("a",)], order_matters=False) is False


def test_result_eq_multiset() -> None:
    r1 = [("a",), ("a",), ("b",)]
    r2 = [("a",), ("b",), ("b",)]
    assert _result_eq(r1, r2, order_matters=False) is False


# ---------------------------------------------------------------------------
# _df_to_tuples
# ---------------------------------------------------------------------------


def test_df_to_tuples_basic() -> None:
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    assert _df_to_tuples(df) == [("Alice", 30), ("Bob", 25)]


def test_df_to_tuples_with_json_list_column() -> None:
    df = pd.DataFrame({"roles": ['["b", "a"]', '["d", "c"]']})
    tuples = _df_to_tuples(df)
    assert tuples == [(("a", "b"),), (("c", "d"),)]


# ---------------------------------------------------------------------------
# CypherBenchEx.compute_async
# ---------------------------------------------------------------------------


def _make_task(
    pred_df: pd.DataFrame | None,
    gold_df: pd.DataFrame | None,
    gold_query_str: str = "MATCH (n) RETURN n.name",
) -> SimpleNL2QTaskOutput:
    return SimpleNL2QTaskOutput(
        qid="t1",
        db="test",
        question="test",
        gold_query=GoldQuery(
            query=gold_query_str,
            exec_result=ExecResult(df=gold_df) if gold_df is not None else None,
        ),
        pred_query=PredQuery(
            query="MATCH (n) RETURN n.name",
            exec_result=ExecResult(df=pred_df) if pred_df is not None else None,
        ),
    )


@pytest.mark.asyncio
async def test_cypherbench_ex_exact_match() -> None:
    df = pd.DataFrame({"name": ["Alice", "Bob"]})
    task = _make_task(df, df)
    assert await CypherBenchEx().compute_async(task) == 1.0


@pytest.mark.asyncio
async def test_cypherbench_ex_row_reorder_unordered() -> None:
    pred = pd.DataFrame({"name": ["Bob", "Alice"]})
    gold = pd.DataFrame({"name": ["Alice", "Bob"]})
    task = _make_task(pred, gold)
    assert await CypherBenchEx().compute_async(task) == 1.0


@pytest.mark.asyncio
async def test_cypherbench_ex_row_reorder_ordered() -> None:
    pred = pd.DataFrame({"name": ["Bob", "Alice"]})
    gold = pd.DataFrame({"name": ["Alice", "Bob"]})
    task = _make_task(pred, gold, gold_query_str="MATCH (n) RETURN n.name ORDER BY n.name")
    assert await CypherBenchEx().compute_async(task) == 0.0


@pytest.mark.asyncio
async def test_cypherbench_ex_column_permutation() -> None:
    pred = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
    gold = pd.DataFrame({"a": ["a", "b"], "b": [1, 2]})
    task = _make_task(pred, gold)
    assert await CypherBenchEx().compute_async(task) == 1.0


@pytest.mark.asyncio
async def test_cypherbench_ex_different_col_count() -> None:
    pred = pd.DataFrame({"x": [1], "y": [2]})
    gold = pd.DataFrame({"a": [1]})
    task = _make_task(pred, gold)
    assert await CypherBenchEx().compute_async(task) == 0.0


@pytest.mark.asyncio
async def test_cypherbench_ex_both_empty() -> None:
    pred = pd.DataFrame()
    gold = pd.DataFrame()
    task = _make_task(pred, gold)
    assert await CypherBenchEx().compute_async(task) == 1.0


@pytest.mark.asyncio
async def test_cypherbench_ex_pred_empty_gold_not() -> None:
    pred = pd.DataFrame()
    gold = pd.DataFrame({"name": ["Alice"]})
    task = _make_task(pred, gold)
    assert await CypherBenchEx().compute_async(task) == 0.0


@pytest.mark.asyncio
async def test_cypherbench_ex_no_pred() -> None:
    gold = pd.DataFrame({"name": ["Alice"]})
    task = _make_task(None, gold)
    assert await CypherBenchEx().compute_async(task) == 0.0


@pytest.mark.asyncio
async def test_cypherbench_ex_multiset_strict() -> None:
    """Duplicate rows must match exactly (no dedup)."""
    pred = pd.DataFrame({"name": ["Alice", "Alice", "Bob"]})
    gold = pd.DataFrame({"name": ["Alice", "Bob", "Bob"]})
    task = _make_task(pred, gold)
    assert await CypherBenchEx().compute_async(task) == 0.0
