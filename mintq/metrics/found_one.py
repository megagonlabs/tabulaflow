from typing import ClassVar
from mintq.schema import (
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    NumericOrNull,
)
from mintq.db_connector import NL2QDBConnector
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_pred_query
from mintq.metrics.simple_ex import SimpleEx


@metric_registry.register
class FoundOne:
    """
    Whether the predicted query match the execution result of one of the gold queries. Only applicable to ambig tasks.
    """

    name: ClassVar[str] = "found_one"
    compatible_output_types: ClassVar[list[str]] = ["ambig-simple", "ambig-flat", "ambig-structured"]

    def __init__(self, abs_tol: float = 1e-2, ignore_repetitions: bool = True):
        self.abs_tol = abs_tol
        self.ignore_repetitions = ignore_repetitions
        self.simple_ex = SimpleEx(self.abs_tol, self.ignore_repetitions)

    async def compute_async(
        self,
        task: SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput,
        db_connector: NL2QDBConnector,
    ) -> NumericOrNull:
        pred_query = get_final_pred_query(task)

        if pred_query is None:
            return 0.0

        if pred_query.exec_result.df is None:  # type: ignore
            return 0.0

        pred_df = pred_query.exec_result.df  # type: ignore

        for gold_query in task.gold_queries:
            gold_dfs = [exec_result.df for exec_result in gold_query.all_exec_results if exec_result.df is not None]
            for gold_df in gold_dfs:
                if self.simple_ex._compare_df(
                    pred_df,
                    gold_df,
                    required_columns=gold_query.required_columns,
                    required_sorted=gold_query.required_sorted,
                ):
                    return 1.0
        return 0.0
