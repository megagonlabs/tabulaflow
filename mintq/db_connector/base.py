from typing import Any, Protocol, Sequence
from sqlalchemy.ext.asyncio import AsyncEngine
import pandas as pd
from mintq.schema import BaseDBSchema, SQLSchema


class BaseAsyncDBConnector(Protocol):
    name: str  # note: for db connectors, name is an instance attribute
    schema: BaseDBSchema

    def __init__(self, name: str, **kwargs: Any): ...

    async def run_query_async(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...


class BaseAsyncSQLDBConnector(Protocol):
    name: str  # note: for db connectors, name is an instance attribute
    schema: SQLSchema
    engine: AsyncEngine

    def __init__(self, name: str, **kwargs: Any): ...

    async def run_query_async(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...
