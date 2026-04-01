"""CypherBench execution accuracy metric.

Faithful reimplementation of the official CypherBench ``execution_accuracy``
metric adapted to work with mintq's DataFrame-based exec-result pipeline.

Reference: ``cypherbench/metrics/execution_accuracy.py`` in
https://github.com/megagonlabs/cypherbench
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from itertools import product
from typing import Any, ClassVar

import pandas as pd

from mintq.db_connector import NL2QDBConnector
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_gold_query, get_final_pred_query
from mintq.schema import NL2QTaskOutput


# ---------------------------------------------------------------------------
# Value normalisation helpers
# ---------------------------------------------------------------------------


def _to_hashable(obj: Any) -> Any:
    """Recursively convert nested structures to a hashable, sorted form.

    Mirrors CypherBench ``to_hashable(obj, unorder_list=True)``.
    """
    if isinstance(obj, (tuple, int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return tuple(sorted(_to_hashable(item) for item in obj))
    if isinstance(obj, set):
        return tuple(sorted(_to_hashable(item) for item in obj))
    if isinstance(obj, dict):
        return tuple(sorted((_to_hashable(k), _to_hashable(v)) for k, v in obj.items()))
    return str(obj)


def _normalize_cell(v: Any) -> Any:
    """Normalize a single DataFrame cell for comparison.

    Handles JSON-stringified lists/dicts produced by ``ExecResult`` sanitisation,
    NaN/None, and standard scalars.
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, (list, dict)):
                return _to_hashable(parsed)
        except (json.JSONDecodeError, ValueError):
            pass
        return v
    if isinstance(v, (int, float, bool)):
        return v
    return _to_hashable(v)


def _df_to_tuples(df: pd.DataFrame) -> list[tuple[Any, ...]]:
    """Convert a DataFrame to ``list[tuple]`` with normalised cell values."""
    return [tuple(_normalize_cell(v) for v in row) for row in df.itertuples(index=False, name=None)]


# ---------------------------------------------------------------------------
# Result-set comparison (ported from CypherBench ``execution_accuracy.py``)
# ---------------------------------------------------------------------------


def _unorder_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(sorted(row, key=lambda x: str(x) + str(type(x))))


def _quick_rej(result1: list[tuple[Any, ...]], result2: list[tuple[Any, ...]], order_matters: bool) -> bool:
    s1 = [_unorder_row(row) for row in result1]
    s2 = [_unorder_row(row) for row in result2]
    return s1 == s2 if order_matters else set(s1) == set(s2)


def _multiset_eq(l1: list[Any], l2: list[Any]) -> bool:
    if len(l1) != len(l2):
        return False
    d: dict[Any, int] = defaultdict(int)
    for e in l1:
        d[e] += 1
    for e in l2:
        d[e] -= 1
        if d[e] < 0:
            return False
    return True


def _get_constraint_permutation(tab1_sets_by_columns: list[set[Any]], result2: list[tuple[Any, ...]]) -> product:  # type: ignore[type-arg]
    num_cols = len(result2[0])
    perm_constraints: list[set[int]] = [set(range(num_cols)) for _ in range(num_cols)]
    if num_cols <= 3:
        return product(*perm_constraints)
    for _ in range(20):
        random_tab2_row = random.choice(result2)
        for tab1_col in range(num_cols):
            for tab2_col in set(perm_constraints[tab1_col]):
                if random_tab2_row[tab2_col] not in tab1_sets_by_columns[tab1_col]:
                    perm_constraints[tab1_col].remove(tab2_col)
    return product(*perm_constraints)


def _result_eq(result1: list[tuple[Any, ...]], result2: list[tuple[Any, ...]], order_matters: bool) -> bool:
    """Check whether two result sets are equivalent under column permutation."""
    if not result1 and not result2:
        return True
    if len(result1) != len(result2):
        return False

    num_cols = len(result1[0])
    if len(result2[0]) != num_cols:
        return False

    if not _quick_rej(result1, result2, order_matters):
        return False

    tab1_sets_by_columns: list[set[Any]] = [{row[i] for row in result1} for i in range(num_cols)]
    for perm in _get_constraint_permutation(tab1_sets_by_columns, result2):
        if len(perm) != len(set(perm)):
            continue
        if num_cols == 1:
            result2_perm = result2
        else:
            result2_perm = [tuple(element[i] for i in perm) for element in result2]
        if order_matters:
            if result1 == result2_perm:
                return True
        else:
            if set(result1) == set(result2_perm) and _multiset_eq(result1, result2_perm):
                return True
    return False


# ---------------------------------------------------------------------------
# Metric class
# ---------------------------------------------------------------------------


@metric_registry.register
class CypherBenchEx:
    """CypherBench execution accuracy (EX).

    Faithful port of the official metric: column-permutation search,
    multiset row comparison, and ORDER BY-aware ordering (inferred from
    the gold Cypher query).
    """

    name: ClassVar[str] = "cypherbench_ex"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: NL2QDBConnector | None = None) -> float:
        pred_query = get_final_pred_query(task, check_exec_result=False, roundtrip_exec_result_csv=False)
        gold_query = get_final_gold_query(task, check_exec_result=False, roundtrip_exec_result_csv=False)

        if pred_query is None or pred_query.exec_result is None or pred_query.exec_result.df is None:
            return 0.0
        if gold_query.exec_result is None or gold_query.exec_result.df is None:
            return 0.0

        pred_tuples = _df_to_tuples(pred_query.exec_result.df)
        gold_tuples = _df_to_tuples(gold_query.exec_result.df)

        if not pred_tuples and not gold_tuples:
            return 1.0
        if not pred_tuples or not gold_tuples:
            return 0.0

        order_matters = gold_query.query is not None and "order by" in gold_query.query.lower()
        return float(_result_eq(gold_tuples, pred_tuples, order_matters=order_matters))
