"""Execution of research query objects against benchmark databases."""

import asyncio

from tabulaflow.data import DBConnector
from tabulaflow.research.types import (
    AmbigNL2QTask,
    FlatAmbigNL2QTaskOutput,
    GoldQuery,
    NL2QTask,
    NL2QTaskOutput,
    PredQuery,
    SimpleAmbigNL2QTaskOutput,
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)


def _task_queries(task: NL2QTask | NL2QTaskOutput) -> list[GoldQuery | PredQuery]:
    if isinstance(task, SimpleNL2QTask):
        queries: list[GoldQuery | PredQuery] = [task.gold_query]
        if isinstance(task, SimpleNL2QTaskOutput) and task.pred_query is not None:
            queries.append(task.pred_query)
        return queries

    if isinstance(task, AmbigNL2QTask):
        queries = list(task.gold_queries)
        if isinstance(task, SimpleAmbigNL2QTaskOutput) and task.pred_intended_query is not None:
            queries.append(task.pred_intended_query)
        elif isinstance(task, (FlatAmbigNL2QTaskOutput, StructuredAmbigNL2QTaskOutput)):
            queries.extend(task.pred_queries)
        return queries

    return []


async def populate_query_exec_result(
    query: GoldQuery | PredQuery,
    db_connector: DBConnector,
    timeout: int | None = None,
    force: bool = False,
) -> None:
    """Execute a query and attach its result unless one is already present."""
    if query.query is None:
        return
    if query.exec_result is not None and not force:
        return
    if timeout is None:
        query.exec_result = await db_connector.run_query_async(
            query.query,
            parameters=query.parameter_values,
        )
    else:
        query.exec_result = await db_connector.run_query_async(
            query.query,
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
    await asyncio.gather(
        *(populate_query_exec_result(query, db_connector, timeout, force) for query in _task_queries(task))
    )
