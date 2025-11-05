import itertools
import re
import copy
import statistics
from typing import Literal, Any
import numpy as np
import pandas as pd
from mintq.schema import AmbigNL2QTask, GoldAmbiguityPoint


def extract_code(response: str) -> str:
    m = re.search(r"```(?:([\w+-]+))?\n([\s\S]*?)\n```", response)
    if m:
        return m.group(2).strip()
    else:
        return response.strip()


def enforce_same_schema(metrics: list[dict[str, Any]]) -> None:
    if not all(m.keys() == metrics[0].keys() for m in metrics):
        raise ValueError("All metrics to aggregate must have the same schema.")
    for k in metrics[0].keys():
        if isinstance(metrics[0][k], dict):
            enforce_same_schema([m[k] for m in metrics])


def aggregate_metrics(
    metrics: list[dict[str, Any]],
    ops: list[Literal["avg", "sum", "max", "min"]] = ["avg", "sum", "max", "min"],
    decimals: int = 4,
) -> dict[str, Any]:
    enforce_same_schema(metrics)

    op2func = {
        "avg": statistics.mean,
        "sum": sum,
        "max": max,
        "min": min,
    }

    res = {}
    for k in metrics[0].keys():
        if isinstance(metrics[0][k], dict):
            res[k] = aggregate_metrics([m[k] for m in metrics], ops, decimals)
        else:
            values = [m[k] for m in metrics if m[k] is not None]
            if values:
                res[k] = {op: round(op2func[op](values), decimals) for op in ops}  # type: ignore
            else:
                res[k] = {op: None for op in ops}
    return res


def sort_gold_queries(task: AmbigNL2QTask) -> AmbigNL2QTask:
    task = copy.deepcopy(task)
    finite_aps = [ap for ap in task.gold_ambiguity_points if ap.type == "finite"]
    gold_query_ids = [
        "GQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes))
        for indexes in itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps])
    ]
    id_to_query = {gq.id: gq for gq in task.gold_queries}
    task.gold_queries = [id_to_query[gq_id] for gq_id in gold_query_ids]
    return AmbigNL2QTask.model_validate(task.model_dump())


def int_to_letter(idx: int) -> str:
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[idx]


def sort_ambiguity_points(task: AmbigNL2QTask) -> AmbigNL2QTask:
    task = copy.deepcopy(task)
    task = sort_gold_queries(task)

    def get_ap_location(ap: GoldAmbiguityPoint) -> tuple[int, int, int]:
        return (task.question.index(ap.phrase), len(ap.phrase), 0 if ap.type == "finite" else 1)

    def get_new_query_id(query_id: str, char_mapping: dict[str, str]) -> str:
        parts = query_id.split("-")
        parts = [parts[0]] + sorted([p.translate(str.maketrans(char_mapping)) for p in parts[1:]])  # type: ignore
        return "-".join(parts)

    # Update the order of ambiguity points
    new_order = sorted(
        range(len(task.gold_ambiguity_points)), key=lambda x: get_ap_location(task.gold_ambiguity_points[x])
    )
    new_gold_ambiguity_points = [task.gold_ambiguity_points[i] for i in new_order]

    # Update the order of SQLs
    finite_aps = [ap for ap in task.gold_ambiguity_points if ap.type == "finite"]
    finite_ap_new_order = sorted(range(len(finite_aps)), key=lambda x: get_ap_location(finite_aps[x]))
    sql_idx = np.arange(len(task.gold_queries))
    sql_idx = sql_idx.reshape([len(ap.interpretations) for ap in finite_aps])  # type: ignore
    sql_idx = np.permute_dims(sql_idx, finite_ap_new_order)
    sql_idx = sql_idx.flatten()
    new_gold_queries = [task.gold_queries[i] for i in sql_idx]

    # Replace the ambiguity point IDs
    task.gold_ambiguity_points = new_gold_ambiguity_points
    task.gold_queries = new_gold_queries
    ap_id_mapping = {ap.id: int_to_letter(i) for i, ap in enumerate(new_gold_ambiguity_points)}
    for ap in task.gold_ambiguity_points:
        ap.id = ap_id_mapping[ap.id]
    for gq in task.gold_queries:
        gq.id = get_new_query_id(gq.id, ap_id_mapping)

    assert task.gold_intended_query_id is not None
    task.gold_intended_query_id = get_new_query_id(task.gold_intended_query_id, ap_id_mapping)

    return AmbigNL2QTask.model_validate(task.model_dump())


def dict_to_df(
    data: dict[str, dict[str, Any]],
    column_level: Literal["outer", "inner"] = "outer",
    add_total_column: bool = True,
    add_total_row: bool = True,
    total_column_only: bool = False,
) -> pd.DataFrame:
    """Convert a dictionary of dictionaries to a dataframe.

    Args:
        data: A dictionary of dictionaries.
        column_level: The outer or inner level keys are used as the columns.
        add_total_column: Whether to add a total column on the rightmost column.
        add_total_row: Whether to add a total row on the bottom row.
        total_column_only: Whether to only include the total column.

    Returns:
        A pandas dataframe.
    """
    outer_keys = list(data.keys())
    inner_keys = list(data[outer_keys[0]].keys())

    if not all(set(inner_keys) == set(data[outer].keys()) for outer in outer_keys):
        raise ValueError("All inner keys must be the same.")

    if column_level == "inner":
        transposed = {inner: {outer: data[outer][inner] for outer in outer_keys} for inner in inner_keys}
        return dict_to_df(transposed, "outer", add_total_column, add_total_row)

    columns, rows = outer_keys, inner_keys
    df = [[data[col][row] for col in columns] for row in rows]
    df = pd.DataFrame(df, columns=columns, index=rows)
    if add_total_row:
        df.loc["Total"] = df.sum(axis=0)
    if add_total_column:
        df.loc[:, "Total"] = df.sum(axis=1)

    if total_column_only and add_total_column:
        df = df.loc[:, ["Total"]]
    return df
