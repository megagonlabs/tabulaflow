from typing import Any, cast

import pandas as pd

from tabulaflow.core import ExecResult
from tabulaflow.data import DBConnector
from tabulaflow.research.query_execution import populate_query_exec_result
from tabulaflow.research.types import PredQuery


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
