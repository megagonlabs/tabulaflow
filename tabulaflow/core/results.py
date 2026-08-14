from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from tabulaflow.core.serialization import _deserialize_dataframe, _sanitize_df, _serialize_dataframe


class ErrorInfo(BaseModel):
    exc_type: str
    message: str


class GraphResultNode(BaseModel):
    """Node in a generic query-result graph view."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str | None = None
    group: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResultEdge(BaseModel):
    """Edge in a generic query-result graph view."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    source: str
    target: str
    label: str | None = None
    directed: bool = True
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResult(BaseModel):
    """Generic node-link graph view attached to a query result."""

    nodes: list[GraphResultNode]
    edges: list[GraphResultEdge]


class ExecResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: pd.DataFrame | None = None
    graph: GraphResult | None = None
    df_is_truncated: bool = False
    """True if the df is truncated, e.g. when the result is too large"""
    affected_rows: int | None = None
    """Rows matched/affected by a single-statement DML (INSERT/UPDATE/DELETE/MERGE),
    when the driver reports it. ``None`` for SELECT, DDL, multi-statement scripts,
    and drivers that don't surface a count. ``0`` means the statement ran but
    matched no rows (e.g. a WHERE that hit nothing) — distinct from ``None``."""
    error: ErrorInfo | None = None
    latency_seconds: float | None = None

    @property
    def succeeded(self) -> bool:
        """Whether the statement executed without error.

        This is the success signal — ``error is None``. It is independent of
        whether the statement produced rows: a successful ``CREATE``/``UPDATE``
        has ``succeeded=True`` but no result set (``df is None``). A result set
        is ``df is not None`` — check that directly."""
        return self.error is None

    @field_serializer("df", when_used="always")
    def serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)

    @model_validator(mode="after")
    def sanitize_df(self) -> "ExecResult":
        if self.df is not None:
            self.df = _sanitize_df(self.df)
        return self

    @model_validator(mode="after")
    def validate_df_or_error(self) -> "ExecResult":
        # Success is ``error is None``; a result set is ``df is not None``. These
        # are independent: a successful non-row statement (DDL/DML) has neither a
        # df nor an error. Only a df *and* an error together is contradictory.
        if self.df is not None and self.error is not None:
            raise ValueError("ExecResult must not carry both df and error")
        return self
