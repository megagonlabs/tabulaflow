from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tabulaflow.core.serialization import SerializableDataFrame


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
    """Outcome of executing one database statement.

    Successful data-producing queries carry ``df``, ``graph``, or both.
    Successful non-row statements may carry ``affected_rows``. Failures carry
    ``error`` and no successful payload. ``latency_seconds`` may accompany any
    outcome.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: SerializableDataFrame | None = None
    graph: GraphResult | None = None
    affected_rows: int | None = Field(default=None, ge=0)
    error: ErrorInfo | None = None
    latency_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @property
    def succeeded(self) -> bool:
        """Whether the statement executed without error.

        This is the success signal — ``error is None``. It is independent of
        whether the statement produced rows: a successful ``CREATE``/``UPDATE``
        has ``succeeded=True`` but no result set (``df is None``). A result set
        is ``df is not None`` — check that directly."""
        return self.error is None

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        has_result = self.df is not None or self.graph is not None
        if self.error is not None and (has_result or self.affected_rows is not None):
            raise ValueError("an error cannot accompany a result or affected-row count")
        if has_result and self.affected_rows is not None:
            raise ValueError("a result cannot carry an affected-row count")
        return self
