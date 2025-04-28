import time
from mintq.db_connector import BaseDBConnector


def gold_executable(
    pred_query: str, gold_query: str, db_connector: BaseDBConnector, timeout: int = 30
) -> float:
    try:
        gold_executed = db_connector.run_query(gold_query, timeout=timeout)
    except Exception as e:
        print(f"Warning: Exception {e} occurred while executing queries")
        return 0.0

    return 1.0
