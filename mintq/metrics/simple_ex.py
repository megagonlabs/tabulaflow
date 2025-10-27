import math
import pandas as pd
from typing import Any, ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_pred_query, get_final_gold_query


@metric_registry.register
class SimpleEx:
    """
    A simple execution accuracy implementation that differes from Spider2's in the following ways:
    - We consider "1.0" == 1.0 == 1 == True, "3.0" == 3.0 == 3
    - We fixed the [-2, 0] != [-2, -0.000001] bug
    - nan
    - inf
    - repetition
    - order
    """

    name: ClassVar[str] = "simple_ex"

    def _is_numerical(self, v: Any) -> bool:
        """The following values are considered numerical:
        - int
        - float
        - bool
        - str that can be converted to float (e.g. "1.0")
        """
        if isinstance(v, (int, float, bool)):
            return True
        if isinstance(v, str):
            try:
                float(v)
                return True
            except (ValueError, TypeError):
                return False
        return False

    def _digest(self, v: Any) -> tuple[Any, ...]:
        if self._is_numerical(v):
            return (v is None, "numerical", v)
        else:
            return (v is None, "non-numerical", str(v))

    def _compare_column(self, pred_col: list[Any], gold_col: list[Any], required_sorted: bool = False) -> bool:
        pred_col = [self._digest(v) for v in pred_col]
        gold_col = [self._digest(v) for v in gold_col]
        if required_sorted:  # required_sorted == True means order matters
            return pred_col == gold_col
        else:
            return sorted(pred_col) == sorted(gold_col)

    def _compare_df(
        self,
        pred_df: pd.DataFrame,
        gold_df: pd.DataFrame,
        required_columns: list[int] | None = None,
        required_sorted: bool = False,
    ) -> float:
        """For each required column (None means all columns), find whether there is a column in predicted df that matches.
        If all required columns are found, return True.
        """
        if required_columns is None:
            required_columns = list(range(len(gold_df.columns)))

        if len(pred_df.columns) < len(required_columns):
            return 0.0

        gold_cols = [gold_df.iloc[:, col_idx].tolist() for col_idx in required_columns]

        for gold_col in gold_cols:
            found_match = False
            for pred_col_idx in range(len(pred_df.columns)):
                pred_col = pred_df.iloc[:, pred_col_idx].tolist()
                if self._compare_column(pred_col, gold_col, required_sorted):
                    found_match = True
                    break

            if not found_match:
                return 0.0

        return 1.0

    async def compute_async(self, task: NL2QTaskOutput) -> float:
        pred_query = get_final_pred_query(task)
        gold_query = get_final_gold_query(task)

        if pred_query is None:
            return 0.0

        if pred_query.exec_result.df is None:  # type: ignore
            return 0.0

        pred_df = pred_query.exec_result.df  # type: ignore
        gold_dfs = [exec_result.df for exec_result in gold_query.all_exec_results if exec_result.df is not None]

        for gold_df in gold_dfs:
            if self._compare_df(
                pred_df,
                gold_df,
                required_columns=gold_query.required_columns,
                required_sorted=gold_query.required_sorted,
            ):
                return 1.0
        return 0.0
