import asyncio
from pathlib import Path
from typing import AsyncGenerator

import pandas as pd
import pytest

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.protocols import ResultTooLargeError
from tabulaflow.data.neo4j import Neo4jConnector
from tabulaflow.data.sql import SQLConnector, ThrottledEngine


class _FakeRecord:
    def __init__(self, value: int) -> None:
        self._value = value

    def values(self) -> list[int]:
        return [self._value]


class _FakeNeo4jResult:
    def __init__(self, values: list[int]) -> None:
        self._records = [_FakeRecord(value) for value in values]
        self.requested_rows: int | None = None

    async def fetch(self, n: int) -> list[_FakeRecord]:
        self.requested_rows = n
        return self._records[:n]

    def keys(self) -> list[str]:
        return ["value"]


class _FakeSession:
    def __init__(self, result: _FakeNeo4jResult) -> None:
        self._result = result

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        pass

    async def run(self, *_args: object, **_kwargs: object) -> _FakeNeo4jResult:
        return self._result


class _FakeDriver:
    def __init__(self, result: _FakeNeo4jResult) -> None:
        self._result = result

    def session(self, *, database: str | None, default_access_mode: str) -> _FakeSession:
        return _FakeSession(self._result)


@pytest.fixture
async def async_connector(tmp_path: Path) -> AsyncGenerator[SQLConnector, None]:
    connector = await SQLConnector.from_url_async(
        global_id="test-result-limit",
        url=f"sqlite+aiosqlite:///{tmp_path / 'result-limit.sqlite'}",
        db_name="result-limit",
        read_only=False,
        config=SQLConnectorConfig(
            max_result_rows=2,
            schema_cache_mode="off",
            query_cache_mode="off",
        ),
    )
    try:
        yield connector
    finally:
        await connector.disconnect_async()


@pytest.mark.asyncio
async def test_throttled_engine_rejects_more_than_max_rows() -> None:
    engine = ThrottledEngine.from_url("duckdb:///:memory:", read_only=False)
    try:
        exact = await engine.execute_async("SELECT * FROM range(2)", return_df=True, max_rows=2)
        assert isinstance(exact.result, pd.DataFrame)
        assert len(exact.result) == 2

        with pytest.raises(ResultTooLargeError, match="more than 2 rows"):
            await engine.execute_async("SELECT * FROM range(3)", return_df=True, max_rows=2)

        unlimited = await engine.execute_async("SELECT * FROM range(3)", return_df=True)
        assert isinstance(unlimited.result, pd.DataFrame)
        assert len(unlimited.result) == 3
    finally:
        await engine.aclose()


@pytest.mark.asyncio
async def test_connector_returns_error_for_oversized_result(
    async_connector: SQLConnector,
) -> None:
    exact = await async_connector.run_query_async("SELECT 1 AS n UNION ALL SELECT 2")
    assert exact.df is not None
    assert len(exact.df) == 2

    oversized = await async_connector.run_query_async("SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3")
    assert oversized.df is None
    assert oversized.error is not None
    assert oversized.error.exc_type == "ResultTooLargeError"
    assert str(oversized.error.message) == ("Query returned more than 2 rows; add a LIMIT, filter, or aggregation")


@pytest.mark.asyncio
async def test_none_disables_connector_result_limit(
    tmp_path: Path,
) -> None:
    connector = await SQLConnector.from_url_async(
        global_id="test-unlimited-result",
        url=f"sqlite+aiosqlite:///{tmp_path / 'unlimited-result.sqlite'}",
        db_name="unlimited-result",
        read_only=False,
        config=SQLConnectorConfig(
            max_result_rows=None,
            schema_cache_mode="off",
            query_cache_mode="off",
        ),
    )
    try:
        result = await connector.run_query_async("SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3")
    finally:
        await connector.disconnect_async()

    assert result.df is not None
    assert len(result.df) == 3


@pytest.mark.asyncio
async def test_neo4j_fetch_is_bounded_before_dataframe_materialization() -> None:
    result = _FakeNeo4jResult([1, 2, 3])
    connector = object.__new__(Neo4jConnector)
    connector._driver = _FakeDriver(result)  # type: ignore[assignment]
    connector._database = None
    connector.read_only = True
    connector._query_semaphore = asyncio.Semaphore(1)

    with pytest.raises(ResultTooLargeError, match="more than 2 rows"):
        await connector._run_cypher("RETURN 1", return_df=True, max_rows=2)

    assert result.requested_rows == 3
