"""Execution of research query objects against benchmark databases."""

import asyncio

from tabulaflow.data import DBConnector
from tabulaflow.research.types import NL2QTask, NL2QTaskOutput


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

        pending = [query for query in queries if force or not query.exec_result]
        if timeout is None:
            results = await asyncio.gather(
                *(db_connector.run_query_async(query.query, parameters=query.parameter_values) for query in pending)
            )
        else:
            results = await asyncio.gather(
                *(
                    db_connector.run_query_async(
                        query.query,
                        parameters=query.parameter_values,
                        timeout=timeout,
                    )
                    for query in pending
                )
            )
        for query, exec_result in zip(pending, results):
            query.exec_result = exec_result
