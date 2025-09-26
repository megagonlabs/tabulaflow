from typing import ClassVar
from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.registry import metric_registry


@metric_registry.register
class BirdSQLEx:
    name: ClassVar[str] = "bird_sql_ex"

    async def compute_async(self, task: SimpleNL2QTaskOutput) -> float:
        if not task.pred_query.exec_result or not task.gold_query.exec_result:
            raise ValueError("ExecResult not populated")

        if task.pred_query.exec_result.df is None or task.gold_query.exec_result.df is None:
            return 0.0

        pred_executed = [row for row in task.pred_query.exec_result.df.itertuples(index=False, name=None)]
        gold_executed = [row for row in task.gold_query.exec_result.df.itertuples(index=False, name=None)]
        if set(pred_executed) == set(gold_executed):
            return 1.0
        return 0.0
