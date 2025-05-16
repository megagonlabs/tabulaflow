from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseDBConnector


class Executable:
    name = "executable"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def compute(self, task: SimpleNL2QTaskOutput, db_connector: BaseDBConnector) -> float:
        try:
            db_connector.run_query(task.pred_query, timeout=self.timeout)
        except Exception as e:
            print(f"Warning: Exception {e} occurred while executing queries")
            return 0.0

        return 1.0
