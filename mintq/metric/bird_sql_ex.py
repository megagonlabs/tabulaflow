from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncSQLDBConnector


class BirdSQLEx:
    name = "bird_sql_ex"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncSQLDBConnector) -> float:
        if not task.gold_exec_results and not task.gold_queries:
            raise ValueError("No gold queries or gold execution results provided")

        try:
            pred_executed = await db_connector.run_query_async(task.pred_query, timeout=self.timeout)
        except Exception:
            return 0.0

        if task.gold_exec_results:
            for exec_result in task.gold_exec_results:
                keys = list(exec_result[0])
                gold_executed = [tuple(row[key] for key in keys) for row in exec_result]
                if set(pred_executed) == set(gold_executed):
                    return 1.0
            return 0.0

        for gold_query in task.gold_queries:
            if task.pred_query == gold_query:
                return 1.0

            try:
                gold_executed = await db_connector.run_query_async(gold_query, timeout=self.timeout)
            except Exception as e:
                print(f"Warning: Exception {e} occurred while executing gold queries")
                continue

            if set(pred_executed) == set(gold_executed):
                return 1.0

        return 0.0
