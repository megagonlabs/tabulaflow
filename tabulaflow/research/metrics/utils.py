"""Shared query and dataframe access for research metrics."""

from io import StringIO

import pandas as pd

from tabulaflow.research.types import (
    FlatAmbigNL2QTaskOutput,
    GoldQuery,
    NL2QTaskOutput,
    PredQuery,
    SimpleAmbigNL2QTaskOutput,
    SimpleNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)

_AMBIG_OUTPUT_TYPES = (
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)


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
    """Return the gold query used to evaluate a task output."""
    query: GoldQuery | None
    if isinstance(task, SimpleNL2QTaskOutput):
        query = task.gold_query
    elif isinstance(task, _AMBIG_OUTPUT_TYPES):
        query = task.gold_intended_query
    else:
        raise ValueError(f"Task type is not supported: {task.task_type}")

    if query is None:
        raise ValueError("Gold query is None")
    if check_exec_result and query.exec_result is None:
        raise ValueError(
            "Gold query has no exec result. If you are running evaluate.py, consider running "
            "populate_exec_results.py first."
        )

    if roundtrip_exec_result_csv:
        query = query.model_copy(deep=True)
        if query.exec_result is not None:
            query.exec_result.df = _roundtrip_df_via_csv(query.exec_result.df)
        for alternative in query.alternative_results:
            alternative.df = _roundtrip_df_via_csv(alternative.df)
    return query


def get_final_pred_query(
    task: NL2QTaskOutput, check_exec_result: bool = True, roundtrip_exec_result_csv: bool = True
) -> PredQuery | None:
    """Return the predicted query used to evaluate a task output."""
    query: PredQuery | None
    if isinstance(task, SimpleNL2QTaskOutput):
        query = task.pred_query
    elif isinstance(task, _AMBIG_OUTPUT_TYPES):
        query = task.pred_intended_query
    else:
        raise ValueError(f"Task type is not supported: {task.task_type}")

    if query is not None and check_exec_result and query.exec_result is None:
        raise ValueError(
            "Pred query has no exec result. If you are running evaluate.py, consider running "
            "populate_exec_results.py first."
        )

    if query is not None and roundtrip_exec_result_csv:
        query = query.model_copy(deep=True)
        if query.exec_result is not None:
            query.exec_result.df = _roundtrip_df_via_csv(query.exec_result.df)
    return query
