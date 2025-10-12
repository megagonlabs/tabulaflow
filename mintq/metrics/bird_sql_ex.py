from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_pred_query, get_final_gold_query


@metric_registry.register
class BirdSQLEx:
    name: ClassVar[str] = "bird_sql_ex"

    async def compute_async(self, task: NL2QTaskOutput) -> float:
        pred_query = get_final_pred_query(task)
        gold_query = get_final_gold_query(task)

        # The agent failed to generate a query
        if pred_query is None:
            return 0.0

        # The generated query is not executable
        if pred_query.exec_result.df is None or gold_query.exec_result.df is None:
            return 0.0

        pred_executed = [row for row in pred_query.exec_result.df.itertuples(index=False, name=None)]
        gold_executed = [row for row in gold_query.exec_result.df.itertuples(index=False, name=None)]
        if set(pred_executed) == set(gold_executed):
            return 1.0
        return 0.0
