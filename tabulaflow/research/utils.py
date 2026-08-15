import copy
import itertools
import statistics
from typing import Any, Coroutine, Literal, cast

import numpy as np
from tqdm.asyncio import tqdm_asyncio

from tabulaflow.research.types import AmbigNL2QTask, GoldAmbiguityPoint, NumericOrNull


def int_to_letter(idx: int) -> str:
    result = ""
    while True:
        result = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[idx % 26] + result
        idx //= 26
        if idx == 0:
            return result
        idx -= 1


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
    sql_idx = sql_idx.reshape([len(ap.interpretations) for ap in finite_aps])
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


def enforce_same_schema(metrics: list[dict[str, Any]]) -> None:
    if not all(metric.keys() == metrics[0].keys() for metric in metrics):
        raise ValueError("All metrics to aggregate must have the same schema.")
    for key in metrics[0]:
        if isinstance(metrics[0][key], dict):
            enforce_same_schema([metric[key] for metric in metrics])


def aggregate_metrics(
    metrics: list[NumericOrNull] | list[dict[str, Any]],
    ops: list[Literal["avg", "sum", "max", "min"]] = ["avg", "sum", "max", "min"],
    decimals: int = 4,
) -> dict[str, Any]:
    if not metrics:
        return {op: None for op in ops}
    if isinstance(metrics[0], dict):
        enforce_same_schema(metrics)  # type: ignore[arg-type]
        return {key: aggregate_metrics([metric[key] for metric in metrics], ops, decimals) for key in metrics[0]}  # type: ignore[index]
    values = [metric for metric in cast(list[NumericOrNull], metrics) if metric is not None]
    if not values:
        return {op: None for op in ops}
    result: dict[str, Any] = {}
    for op in ops:
        if op == "avg":
            value = statistics.mean(values)
        elif op == "sum":
            value = sum(values)
        elif op == "max":
            value = max(values)
        else:
            value = min(values)
        result[op] = round(value, decimals)
    return result


def flatten_dict(data: dict[str, Any], sep: str = ".") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result.update(
                {
                    f"{key}{sep}{nested_key}": nested_value
                    for nested_key, nested_value in flatten_dict(value, sep).items()
                }
            )
        else:
            result[key] = value
    return result


def pprint_dict(data: dict[str, Any]) -> str:
    return "\n".join(
        f"- {key}: {'N/A' if value is None else f'{value:.4f}'}" for key, value in flatten_dict(data).items()
    )


async def tqdm_gather_with_exceptions(
    *fs: Coroutine[Any, Any, Any], return_exceptions: bool = False, **kwargs: Any
) -> list[Any]:
    if not return_exceptions:
        return await tqdm_asyncio.gather(*fs, **kwargs)  # type: ignore[no-any-return]

    async def wrap(f: Coroutine[Any, Any, Any]) -> Any:
        try:
            return await f
        except Exception as exc:
            return exc

    return await tqdm_asyncio.gather(*map(wrap, fs), **kwargs)  # type: ignore[no-any-return]


def dict_to_df(
    data: dict[str, dict[str, Any]],
    column_level: Literal["outer", "inner"] = "outer",
    add_total_column: bool = True,
    add_total_row: bool = True,
    total_column_only: bool = False,
) -> Any:
    import pandas as pd

    outer_keys = list(data)
    inner_keys = list(data[outer_keys[0]])
    if not all(set(inner_keys) == set(data[outer]) for outer in outer_keys):
        raise ValueError("All inner keys must be the same.")
    if column_level == "inner":
        transposed = {inner: {outer: data[outer][inner] for outer in outer_keys} for inner in inner_keys}
        return dict_to_df(transposed, "outer", add_total_column, add_total_row)
    df = pd.DataFrame(
        [[data[column][row] for column in outer_keys] for row in inner_keys], columns=outer_keys, index=inner_keys
    )
    if add_total_row:
        df.loc["Total"] = df.sum(axis=0)
    if add_total_column:
        df.loc[:, "Total"] = df.sum(axis=1)
    return df.loc[:, ["Total"]] if total_column_only and add_total_column else df
