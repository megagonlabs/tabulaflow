from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.db_connector import NL2QDBConnector
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_pred_query, get_final_gold_query


@metric_registry.register
class BirdSQLEx:
    name: ClassVar[str] = "bird_sql_ex"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: NL2QDBConnector) -> float:
        pred_query = get_final_pred_query(task)
        gold_query = get_final_gold_query(task)

        # The agent failed to generate a query
        if pred_query is None:
            return 0.0

        # The generated query is not executable
        if pred_query.exec_result.df is None or gold_query.exec_result.df is None:  # type: ignore
            return 0.0

        pred_executed = [row for row in pred_query.exec_result.df.itertuples(index=False, name=None)]  # type: ignore
        gold_executed = [row for row in gold_query.exec_result.df.itertuples(index=False, name=None)]  # type: ignore
        if set(pred_executed) == set(gold_executed):
            return 1.0
        return 0.0
