import math
import pandas as pd
from typing import Any, ClassVar
from mintq.schema import SimpleNL2QTaskOutput
from mintq.metrics.base import metric_registry


# Borrowed from https://github.com/xlang-ai/Spider2/blob/main/spider2-snow/evaluation_suite/evaluate.py
def compare_multi_pandas_table(
    pred: pd.DataFrame, multi_gold: list[pd.DataFrame], multi_condition_cols: Any = [], ignore_order: bool = False
) -> float:
    print("multi_condition_cols", multi_condition_cols)

    if (
        multi_condition_cols == []
        or multi_condition_cols == [[]]
        or multi_condition_cols == [None]
        or multi_condition_cols is None
    ):
        multi_condition_cols = [[] for _ in range(len(multi_gold))]
    elif len(multi_gold) > 1 and not all(isinstance(sublist, list) for sublist in multi_condition_cols):
        multi_condition_cols = [multi_condition_cols for _ in range(len(multi_gold))]
    multi_ignore_order = [ignore_order for _ in range(len(multi_gold))]

    for i, gold in enumerate(multi_gold):
        if compare_pandas_table(pred, gold, multi_condition_cols[i], multi_ignore_order[i]):
            return 1.0
    return 0.0


# Borrowed from https://github.com/xlang-ai/Spider2/blob/main/spider2-snow/evaluation_suite/evaluate.py
def compare_pandas_table(
    pred: pd.DataFrame, gold: pd.DataFrame, condition_cols: list[int] = [], ignore_order: bool = False
) -> float:
    """_summary_

    Args:
        pred (Dataframe): _description_
        gold (Dataframe): _description_
        condition_cols (list, optional): _description_. Defaults to [].
        ignore_order (bool, optional): _description_. Defaults to False.

    """
    tolerance = 1e-2

    def vectors_match(v1: list[Any], v2: list[Any], tol: float = tolerance, ignore_order_: bool = False) -> bool:
        if ignore_order_:
            v1, v2 = (
                sorted(v1, key=lambda x: (x is None, str(x), isinstance(x, (int, float)))),
                sorted(v2, key=lambda x: (x is None, str(x), isinstance(x, (int, float)))),
            )
        if len(v1) != len(v2):
            return False
        for a, b in zip(v1, v2):
            if pd.isna(a) and pd.isna(b):
                continue
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                if not math.isclose(float(a), float(b), abs_tol=tol):
                    return False
            elif a != b:
                return False
        return True

    if condition_cols != []:
        gold_cols = gold.iloc[:, condition_cols]
    else:
        gold_cols = gold
    pred_cols = pred

    t_gold_list = gold_cols.transpose().values.tolist()
    t_pred_list = pred_cols.transpose().values.tolist()
    score = 1.0
    for _, gold in enumerate(t_gold_list):
        if not any(vectors_match(gold, pred, ignore_order_=ignore_order) for pred in t_pred_list):
            score = 0.0
    return score


@metric_registry.register
class Spider2Ex:
    name: ClassVar[str] = "spider2_ex"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def compute_async(self, task: SimpleNL2QTaskOutput) -> float:
        if not task.pred_query.exec_result or not task.gold_query.exec_result:
            raise ValueError("ExecResult not populated")

        if task.pred_query.exec_result.error:
            return 0.0

        pred_df = task.pred_query.exec_result.df
        gold_dfs = [exec_result.df for exec_result in task.gold_query.all_exec_results if exec_result.df is not None]

        if not gold_dfs:
            return 0.0
        elif len(gold_dfs) == 1:
            return compare_pandas_table(
                pred_df,
                gold_dfs[0],
                task.extra_info.get("condition_cols", []),
                task.extra_info.get("ignore_order", False),
            )
        else:
            return compare_multi_pandas_table(
                pred_df, gold_dfs, task.extra_info.get("condition_cols", []), task.extra_info.get("ignore_order", False)
            )
