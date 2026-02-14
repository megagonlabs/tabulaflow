import itertools
import re
import copy
import statistics
from typing import Literal, Any, Coroutine

import numpy as np
import pandas as pd
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import build_scope, Scope
from tqdm.asyncio import tqdm_asyncio

from mintq.schema import AmbigNL2QTask, GoldAmbiguityPoint, NumericOrNull


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
    metrics: list[NumericOrNull] | list[dict[str, Any]],
    ops: list[Literal["avg", "sum", "max", "min"]] = ["avg", "sum", "max", "min"],
    decimals: int = 4,
) -> dict[str, Any]:
    if not metrics:
        return {op: None for op in ops}

    if isinstance(metrics[0], dict):
        enforce_same_schema(metrics)  # type: ignore
        res = {}
        for k in metrics[0].keys():
            res[k] = aggregate_metrics([m[k] for m in metrics], ops, decimals)  # type: ignore
        return res

    op2func = {
        "avg": statistics.mean,
        "sum": sum,
        "max": max,
        "min": min,
    }

    values = [m for m in metrics if m is not None]
    if values:
        return {op: round(op2func[op](values), decimals) for op in ops}  # type: ignore
    else:
        return {op: None for op in ops}


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
    """Convert an integer index to a letter representation (A, B, ..., Z, AA, AB, ...)."""
    result = ""
    while True:
        result = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[idx % 26] + result
        idx = idx // 26
        if idx == 0:
            break
        idx -= 1  # Adjust for 0-indexing (A=0, Z=25, AA=26)
    return result


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


def flatten_dict(d: dict[str, Any], sep: str = ".") -> dict[str, Any]:
    """
    Example:
      Input: {"a": {"b": 1, "c": 2}, "d": {"e": 3, "f": 4}}
      Output: {"a.b": 1, "a.c": 2, "d.e": 3, "d.f": 4}
    """
    result = {}
    for key, value in d.items():
        if isinstance(value, dict):
            nested = flatten_dict(value, sep)
            for nested_key, nested_value in nested.items():
                result[f"{key}{sep}{nested_key}"] = nested_value
        else:
            result[key] = value
    return result


def pprint_dict(d: dict[str, Any]) -> str:
    """
    Example:
      Input: {"a": {"b": 0.1234, "c": 0.0345}, "d": {"e": 3.1234, "f": 4.0000}}
      Output:
      ```
      - a.b: 0.1234
      - a.c: 0.0345
      - d.e: 3.1234
      - d.f: 4.0000
      ```
    """
    flattened = flatten_dict(d)
    res = []
    for key, value in flattened.items():
        res.append(f"- {key}: {'N/A' if value is None else f'{value:.4f}'}")
    return "\n".join(res)


async def tqdm_gather_with_exceptions(
    *fs: Coroutine[Any, Any, Any], return_exceptions: bool = False, **kwargs: Any
) -> list[Any]:
    """
    A progress bar wrapper for tqdm_asyncio.gather that supports return_exceptions.
    See https://github.com/tqdm/tqdm/issues/1286 for more details.
    """
    if not return_exceptions:
        return await tqdm_asyncio.gather(*fs, **kwargs)  # type: ignore

    async def wrap(f: Coroutine[Any, Any, Any]) -> Any:
        try:
            return await f
        except Exception as e:
            return e

    return await tqdm_asyncio.gather(*map(wrap, fs), **kwargs)  # type: ignore


def extract_all_source_columns(query: str, language: str = "sqlite") -> list[tuple[str, str]]:
    """
    Extracts ALL source columns used anywhere in the query (SELECT, WHERE, JOIN, ORDER BY, GROUP BY, etc.).

    Resolves table aliases and traces columns through CTEs and subqueries back to their
    original source tables.

    Args:
        query: SQL query string to analyze
        language: SQL dialect for parsing (e.g., "sqlite", "postgres", "mysql", "snowflake")

    Returns:
        List of (table_name, column_name) tuples for all source columns referenced
        in the query. Returns an empty list if the query cannot be parsed.

    Example:
        >>> query = '''
        ... WITH recent_orders AS (
        ...   SELECT o.user_id, o.total, o.order_dates
        ...   FROM orders o
        ... )
        ... SELECT u.id, ro.total
        ... FROM users u
        ... JOIN recent_orders ro ON u.id = ro.user_id
        ... '''
        >>> extract_all_source_columns(query)
        [('orders', 'user_id'), ('orders', 'total'), ('orders', 'order_dates'), ('users', 'id')]
    """
    try:
        parsed = sqlglot.parse_one(query, dialect=language)
        qualified = qualify(parsed, dialect=language, validate_qualify_columns=False)
        root = build_scope(qualified)
    except Exception:
        # Dialect-specific parsing can fail on valid SQL (e.g. Snowflake TRIM(BOTH '(' FROM ...)).
        # Fall back to permissive dialect-free parsing.
        try:
            parsed = sqlglot.parse_one(query)
            qualified = qualify(parsed, validate_qualify_columns=False)
            root = build_scope(qualified)
        except Exception:
            return []

    if root is None:
        return []

    def collect_columns(scope: Scope, result: list[tuple[str, str]], seen: set[tuple[str, str]]) -> None:
        """Recursively collect source columns from a scope and all nested scopes."""
        for col in scope.columns:
            table_alias = col.table
            col_name = col.name

            source = scope.sources.get(table_alias)
            if isinstance(source, exp.Table):
                table_name = source.name
                key = (table_name, col_name)
                if key not in seen:
                    result.append(key)
                    seen.add(key)

        # Process UNION scopes (each SELECT in a UNION/UNION ALL)
        for union_scope in scope.union_scopes:
            collect_columns(union_scope, result, seen)

        # Process CTE scopes (WITH clause definitions)
        for cte_scope in scope.cte_scopes:
            collect_columns(cte_scope, result, seen)

        # Process subquery scopes (subqueries in WHERE, HAVING, etc.)
        for subquery_scope in scope.subquery_scopes:
            collect_columns(subquery_scope, result, seen)

        # Process derived table scopes (subqueries in FROM/JOIN)
        for source in scope.sources.values():
            if isinstance(source, Scope):
                collect_columns(source, result, seen)

    result: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    collect_columns(root, result, seen)
    return result
