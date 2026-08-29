from typing import Any, cast

import pandas as pd

from tabulaflow.core import ExecResult
from tabulaflow.data import DBConnector
from tabulaflow.research.query_execution import populate_query_exec_result, populate_task_exec_results
from tabulaflow.research.types import FlatAmbigNL2QTaskOutput, GoldQuery, PredQuery, SimpleNL2QTaskOutput


class _Connector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def run_query_async(self, query: str, **kwargs: Any) -> ExecResult:
        self.calls.append((query, kwargs))
        return ExecResult(df=pd.DataFrame({"value": [1]}))


async def test_populate_query_exec_result_executes_missing_result() -> None:
    connector = _Connector()
    query = PredQuery(query="SELECT :value", parameter_values={"value": 1})

    await populate_query_exec_result(query, cast(DBConnector, connector), timeout=30)

    assert query.exec_result is not None
    assert connector.calls == [("SELECT :value", {"parameters": {"value": 1}, "timeout": 30})]


async def test_populate_query_exec_result_skips_existing_result_unless_forced() -> None:
    connector = _Connector()
    existing = ExecResult(df=pd.DataFrame({"value": [0]}))
    query = PredQuery(query="SELECT 1", exec_result=existing)

    await populate_query_exec_result(query, cast(DBConnector, connector))
    assert query.exec_result is existing
    assert connector.calls == []

    await populate_query_exec_result(query, cast(DBConnector, connector), force=True)
    assert query.exec_result is not existing
    assert connector.calls == [("SELECT 1", {"parameters": {}})]


async def test_populate_query_exec_result_skips_missing_query_text() -> None:
    connector = _Connector()

    await populate_query_exec_result(GoldQuery(query=None), cast(DBConnector, connector))

    assert connector.calls == []


async def test_populate_task_exec_results_executes_simple_queries_once() -> None:
    connector = _Connector()
    task = SimpleNL2QTaskOutput(
        qid="q1",
        db="db",
        question="Return one.",
        gold_query=GoldQuery(query="gold"),
        pred_query=PredQuery(query="pred"),
    )

    await populate_task_exec_results(task, cast(DBConnector, connector))

    assert [query for query, _ in connector.calls] == ["gold", "pred"]


async def test_populate_task_exec_results_does_not_duplicate_ambiguous_intended_query() -> None:
    connector = _Connector()
    task = FlatAmbigNL2QTaskOutput(
        qid="q1",
        has_intended_resolution=False,
        db="db",
        question="Return one.",
        gold_ambiguity_points=[],
        gold_queries=[GoldQuery(id="GQRY", query="gold")],
        gold_intended_query_id=None,
        interpretations=[],
        parameters=[],
        pred_queries=[PredQuery(id="PQRY-0", query="pred")],
        pred_intended_query_id="PQRY-0",
    )

    await populate_task_exec_results(task, cast(DBConnector, connector))

    assert [query for query, _ in connector.calls] == ["gold", "pred"]
