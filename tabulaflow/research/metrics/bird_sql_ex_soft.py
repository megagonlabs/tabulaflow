import math
from typing import Any, ClassVar
from itertools import combinations
from tabulaflow.research.types import NL2QTaskOutput
from tabulaflow.data import DBConnector
from tabulaflow.research.metrics.base import metric_registry
from tabulaflow.research.metrics.utils import get_final_pred_query, get_final_gold_query

_MAX_COLUMN_COMBINATIONS = 1000


@metric_registry.register
class BirdSQLExSoft:
    name: ClassVar[str] = "bird_sql_ex_soft"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    def _compare(self, pred_executed: list[tuple[Any, ...]], gold_executed: list[tuple[Any, ...]]) -> float:
        if not gold_executed and not pred_executed:
            return 1.0
        elif not gold_executed or not pred_executed:
            return 0.0

        n_cols_gold = len(gold_executed[0])
        n_cols_pred = len(pred_executed[0])

        # Determine whether there exists a subset of columns in pred_executed that is equal to gold_executed
        if n_cols_gold > n_cols_pred:
            return 0.0

        # Skip if the combinatorial space is too large (e.g. C(24,12) = 2.7M)
        if math.comb(n_cols_pred, n_cols_gold) > _MAX_COLUMN_COMBINATIONS:
            return 0.0

        # Convert results to sets of tuples for comparison
        gold_set = set(tuple(row) for row in gold_executed)

        # Try all possible column combinations of pred_executed that match gold_executed's width
        for col_indices in combinations(range(n_cols_pred), n_cols_gold):
            # Extract the subset of columns from pred_executed
            pred_subset = set(tuple(row[i] for i in col_indices) for row in pred_executed)

            # If we found a matching subset, return 1.0
            if pred_subset == gold_set:
                return 1.0
        return 0.0

    async def compute_async(self, task: NL2QTaskOutput, db_connector: DBConnector | None = None) -> float:
        pred_query = get_final_pred_query(task)
        gold_query = get_final_gold_query(task)

        if pred_query is None:
            return 0.0

        if pred_query.exec_result.df is None or gold_query.exec_result.df is None:  # type: ignore
            return 0.0

        pred_executed = [row for row in pred_query.exec_result.df.itertuples(index=False, name=None)]  # type: ignore
        gold_executed = [row for row in gold_query.exec_result.df.itertuples(index=False, name=None)]  # type: ignore
        if self._compare(pred_executed, gold_executed) == 1.0:
            return 1.0
        return 0.0
