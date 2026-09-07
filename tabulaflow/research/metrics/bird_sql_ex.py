from typing import ClassVar
from tabulaflow.research.types import NL2QTaskOutput
from tabulaflow.data import DataConnector
from tabulaflow.research.metrics.registry import metric_registry
from tabulaflow.research.metrics.utils import get_final_gold_query, get_final_pred_query


@metric_registry.register
class BirdSQLEx:
    name: ClassVar[str] = "bird_sql_ex"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: DataConnector | None = None) -> float:
        pred_query = get_final_pred_query(task)
        gold_query = get_final_gold_query(task)

        # The agent failed to generate a query
        if pred_query is None:
            return 0.0

        assert pred_query.exec_result is not None and gold_query.exec_result is not None
        pred_df = pred_query.exec_result.df
        gold_df = gold_query.exec_result.df
        if pred_df is None or gold_df is None:
            return 0.0

        pred_executed = list(pred_df.itertuples(index=False, name=None))
        gold_executed = list(gold_df.itertuples(index=False, name=None))
        if set(pred_executed) == set(gold_executed):
            return 1.0
        return 0.0
