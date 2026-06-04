from typing import ClassVar
from tabulaflow.core.types import NumericOrNull
from tabulaflow.research.types import (
    NL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)
from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.research.metrics.base import metric_registry
from tabulaflow.research.metrics.utils import get_final_pred_query
from tabulaflow.research.metrics.simple_ex import SimpleEx

AmbigTaskOutput = SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput


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
        task: NL2QTaskOutput,
        db_connector: NL2QDBConnector | None = None,
    ) -> NumericOrNull:
        assert isinstance(task, AmbigTaskOutput)
        pred_query = get_final_pred_query(task)

        if pred_query is None:
            return 0.0

        if pred_query.exec_result.df is None:  # type: ignore
            return 0.0

        pred_df = pred_query.exec_result.df  # type: ignore

        for gold_query in task.gold_queries:
            if self.simple_ex._compare_df(
                pred_df,
                gold_query.exec_result.df,  # type: ignore
                required_columns=gold_query.required_columns,
                required_sorted=gold_query.required_sorted,
            ):
                return 1.0
            for alt_result in gold_query.alternative_results:
                if self.simple_ex._compare_df(
                    pred_df,
                    alt_result.df,
                    required_sorted=gold_query.required_sorted,
                ):
                    return 1.0
        return 0.0
