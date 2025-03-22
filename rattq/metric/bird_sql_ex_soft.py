import time
from rattq.db_connector import BaseDBConnector
from itertools import combinations


def bird_sql_ex_soft(
    pred_query: str, gold_query: str, db_connector: BaseDBConnector, timeout: int = 30
) -> float:
    if pred_query == gold_query:
        return 1.0
    t0 = time.time()

    try:
        gold_executed = db_connector.run_query(gold_query, timeout=timeout)
        pred_executed = db_connector.run_query(pred_query, timeout=timeout)
    except Exception as e:
        print(f"Warning: Exception {e} occurred while executing queries")
        return 0.0

    if not gold_executed and not pred_executed:
        return 1.0
    elif not gold_executed or not pred_executed:
        return 0.0

    n_cols_gold = len(gold_executed[0])
    n_cols_pred = len(pred_executed[0])

    # Determine whether there exists a subset of columns in pred_executed that is equal to gold_executed
    if n_cols_gold > n_cols_pred:
        return 0.0

    # Convert results to sets of tuples for comparison
    gold_set = set(tuple(row) for row in gold_executed)

    # Try all possible column combinations of pred_executed that match gold_executed's width
    for col_indices in combinations(range(n_cols_pred), n_cols_gold):
        # Extract the subset of columns from pred_executed
        pred_subset = set(tuple(row[i] for i in col_indices) for row in pred_executed)

        # If we found a matching subset, return 1.0
        if pred_subset == gold_set:
            return 1.0

    # No matching subset found
    return 0.0
