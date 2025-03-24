import time
from rattq.db_connector import BaseDBConnector


def bird_sql_ex(
    pred_query: str, gold_query: str, db_connector: BaseDBConnector, timeout: int = 30
) -> float:
    if pred_query == gold_query:
        return 1.0

    try:
        gold_executed = db_connector.run_query(gold_query, timeout=timeout)
        pred_executed = db_connector.run_query(pred_query, timeout=timeout)
    except Exception as e:
        print(f"Warning: Exception {e} occurred while executing queries")
        return 0.0

    return float(set(pred_executed) == set(gold_executed))
