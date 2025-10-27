import math
import pandas as pd
from typing import Any, ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_pred_query, get_final_gold_query


@metric_registry.register
class SimpleEx:
    """
    A simple execution accuracy implementation.

    Features that are different from Spider2's EX implementation:
    - For boolean values, we consider True == 1 == "1.0" == 1.0
    - For convertible string values, we consider "3.0" == 3.0 == 3
    - We consider "nan" == None == math.nan == np.nan
    - We fixed the [-2, 0] != [-2, -0.000001] bug
    - Row order does not matter by default

    Features that are the same as Spider2's EX implementation:
    - Repetitions are considered
    - Column order does not matter
    - Additional columns are allowed
    """

    name: ClassVar[str] = "simple_ex"

    def __init__(self, abs_tol: float = 1e-2):
        self.abs_tol = abs_tol

    def _digest(self, v: Any) -> tuple[Any, ...]:
        """The following values are considered numerical:
        - int
        - float
        - bool
        - str that can be converted to float (e.g. "1.0")
        """
        if pd.isna(v):
            return ("nan", None)
        elif isinstance(v, (int, float, bool)):
            return ("numerical", float(v))
        elif isinstance(v, str):
            try:
                v_float = float(v)
                return ("numerical", v_float) if not pd.isna(v_float) else ("nan", None)
            except (ValueError, TypeError):
                return ("object", str(v))
        else:
            return ("object", str(v))

    def _compare_column(self, pred_col: list[Any], gold_col: list[Any], required_sorted: bool = False) -> bool:
        pred_col = [self._digest(v) for v in pred_col]
        gold_col = [self._digest(v) for v in gold_col]
        if not required_sorted:  # required_sorted == False means order does not matter
            pred_col = sorted(pred_col)
            gold_col = sorted(gold_col)
        if len(pred_col) != len(gold_col):
            return False
        for (pred_type, pred_value), (gold_type, gold_value) in zip(pred_col, gold_col):
            if pred_type == gold_type == "numerical":
                if not math.isclose(pred_value, gold_value, abs_tol=self.abs_tol):
                    return False
            elif (pred_type, pred_value) != (gold_type, gold_value):
                return False
        return True

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
        required_columns = required_columns or list(range(len(gold_df.columns)))
        if len(pred_df.columns) < len(required_columns):
            return 0.0

        gold_cols = [gold_df.iloc[:, col_idx].tolist() for col_idx in required_columns]
        for gold_col in gold_cols:
            if not any(
                self._compare_column(pred_df.iloc[:, pred_col_idx].tolist(), gold_col, required_sorted)
                for pred_col_idx in range(len(pred_df.columns))
            ):
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
