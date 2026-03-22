from io import StringIO
import pandas as pd
from mintq.schema import NL2QTaskOutput, PredQuery, GoldQuery

DATASET_DEFAULT_METRICS: dict[str, str] = {
    "bird-sql": "bird_sql_ex",
    "spider2-snow": "spider2_ex",
    "spider2-lite": "spider2_ex",
    "spider2-dbt": "spider2_duckdb_match",
    "beaver": "simple_ex",
    "arcs": "simple_ex",
    "ambrosia-s": "simple_ex",
}


def get_default_metric(dataset: str) -> str:
    """Returns the default evaluation metric name for a dataset."""
    metric = DATASET_DEFAULT_METRICS.get(dataset)
    if metric is None:
        raise ValueError(
            f"No default metric for dataset '{dataset}'. Specify --metric explicitly."
        )
    return metric


def _roundtrip_df_via_csv(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None:
        return None
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return pd.read_csv(csv_buffer)


def get_final_gold_query(
    task: NL2QTaskOutput, check_exec_result: bool = True, roundtrip_exec_result_csv: bool = True
) -> GoldQuery:
    if task.task_type == "simple":
        res = task.gold_query
    elif task.task_type == "ambig":
        res = task.gold_intended_query  # type: ignore
    else:
        raise ValueError(f"Task type is not supported: {task.task_type}")

    if res is not None and check_exec_result and res.exec_result is None:
        raise ValueError(
            "Gold query has no exec result. If you are running evaluate.py, consider running populate_exec_results.py first."
        )

    if res is None:
        raise ValueError("Gold query is None")

    if roundtrip_exec_result_csv:
        res = res.model_copy(deep=True)
        if res.exec_result is not None:
            res.exec_result.df = _roundtrip_df_via_csv(res.exec_result.df)
        for alt_result in res.alternative_results:
            alt_result.df = _roundtrip_df_via_csv(alt_result.df)

    return res


def get_final_pred_query(
    task: NL2QTaskOutput, check_exec_result: bool = True, roundtrip_exec_result_csv: bool = True
) -> PredQuery | None:
    if task.task_type == "simple":
        res = task.pred_query
    elif task.task_type == "ambig":
        res = task.pred_intended_query
    else:
        raise ValueError(f"Task type is not supported: {task.task_type}")

    if res is not None and check_exec_result and res.exec_result is None:
        raise ValueError(
            "Pred query has no exec result. If you are running evaluate.py, consider running populate_exec_results.py first."
        )

    if res is not None and roundtrip_exec_result_csv:
        res = res.model_copy(deep=True)
        if res.exec_result is not None:
            res.exec_result.df = _roundtrip_df_via_csv(res.exec_result.df)

    return res
