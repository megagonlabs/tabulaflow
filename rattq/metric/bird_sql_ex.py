import time
from rattq.db_connector import BaseDBConnector


def bird_sql_ex(pred_query: str,
                gold_query: str,
                db_connector: BaseDBConnector,
                timeout: int = 30) -> float:
    if pred_query == gold_query:
        return 1.0
    t0 = time.time()
    gold_executed = db_connector.run_query(gold_query)
    gold_seconds = time.time() - t0
    if gold_seconds > timeout:
        print(f"Warning: Execution of gold query {gold_query} took longer than {timeout} seconds")
    try:
        pred_executed = db_connector.run_query(pred_query, timeout=timeout)
    except Exception as e:
        print(f"Warning: Exception {e} occurred while executing the predicted query {pred_query}")
        return 0.0

    return int(set(pred_executed) == set(gold_executed))
