from typing import Any, Protocol, Sequence
import sqlalchemy
import pandas as pd
from mintq.schema import BaseDBSchema, SQLSchema


class BaseDBConnector(Protocol):
    name: str  # note: for db connectors, name is an instance attribute
    schema: BaseDBSchema

    def __init__(self, name: str, **kwargs: Any): ...

    def run_query(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...


class BaseSQLDBConnector(Protocol):
    name: str
    schema: SQLSchema
    engine: sqlalchemy.engine.Engine

    def __init__(self, name: str, **kwargs: Any): ...

    def run_query(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...
