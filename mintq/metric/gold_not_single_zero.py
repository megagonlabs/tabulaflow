import time
from mintq.db_connector import BaseDBConnector


def gold_not_single_zero(
    pred_query: str, gold_query: str, db_connector: BaseDBConnector, timeout: int = 30
) -> float:
    try:
        gold_executed = db_connector.run_query(gold_query, timeout=timeout)
    except Exception as e:
        print(f"Warning: Exception {e} occurred while executing queries")
        return 0.0

    if len(gold_executed) == 1 and len(gold_executed[0]) == 1 and gold_executed[0][0] == 0:
        return 0.0

    return 1.0
