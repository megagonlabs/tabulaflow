"""Execution of research query objects against benchmark databases."""

import asyncio

from tabulaflow.data import DBConnector
from tabulaflow.research.types import GoldQuery, NL2QTask, NL2QTaskOutput, PredQuery


async def populate_query_exec_result(
    query: GoldQuery | PredQuery,
    db_connector: DBConnector,
    timeout: int | None = None,
    force: bool = False,
) -> None:
    """Execute a query and attach its result unless one is already present."""
    if query.exec_result is not None and not force:
        return
    if timeout is None:
        query.exec_result = await db_connector.run_query_async(
            query.query,  # type: ignore[arg-type]
            parameters=query.parameter_values,
        )
    else:
        query.exec_result = await db_connector.run_query_async(
            query.query,  # type: ignore[arg-type]
            parameters=query.parameter_values,
            timeout=timeout,
        )


async def populate_task_exec_results(
    task: NL2QTask | NL2QTaskOutput,
    db_connector: DBConnector,
    timeout: int | None = None,
    force: bool = False,
) -> None:
    """Execute missing gold and predicted queries attached to one task."""
    if task.task_type == "dbt":
        return

    for prefix in ("gold", "pred"):
        queries = []
        if query := getattr(task, f"{prefix}_query", None):
            queries.append(query)
        if intended_query := getattr(task, f"{prefix}_intended_query", None):
            queries.append(intended_query)
        if query_list := getattr(task, f"{prefix}_queries", None):
            queries.extend(query_list)

        await asyncio.gather(*(populate_query_exec_result(query, db_connector, timeout, force) for query in queries))
