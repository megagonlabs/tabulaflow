"""The chat-turn result view-model — the ``Finished`` event payload.

Pydantic models (consistent with the rest of the data layer in ``core.types`` /
``research.types``), so the whole chat⇄frontend contract is wire-serializable.
The DataFrame field reuses the same Arrow serializer as ``core.ExecResult``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.types import Usage


class ChatResultRecord(BaseModel):
    """Display-ready data for one referenced query result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["record"] = "record"
    record_id: str
    label: str | None
    query: str | None
    df: pd.DataFrame | None
    chart_spec: dict[str, Any] | None
    query_lexer: str = "sql"

    @field_serializer("df", when_used="always")
    def _serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def _deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)


class ChatResultMap(BaseModel):
    """Display-ready data for one cited map artifact.

    A standalone, map-only card assembled from one or more query results. Its
    normalized ``map_spec`` layers each name the ``source`` record they read from;
    ``sources`` holds those records' DataFrames keyed by record id.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["map"] = "map"
    map_id: str
    label: str | None
    map_spec: dict[str, Any]
    sources: dict[str, pd.DataFrame]

    @field_serializer("sources", when_used="always")
    def _serialize_sources(self, sources: dict[str, pd.DataFrame]) -> dict[str, Any]:
        return {rid: _serialize_dataframe(df) for rid, df in sources.items()}

    @field_validator("sources", mode="before")
    @classmethod
    def _deserialize_sources(cls, v: dict[str, Any]) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for rid, df in (v or {}).items():
            deserialized = _deserialize_dataframe(df)
            if deserialized is not None:
                out[rid] = deserialized
        return out


# A cited artifact is either a query result (record) or a standalone map,
# discriminated by ``kind``; ``ChatResult.artifacts`` holds them in citation order.
ChatResultArtifact = Annotated[ChatResultRecord | ChatResultMap, Field(discriminator="kind")]


class ChatResult(BaseModel):
    """The complete result of a single chat turn (the ``Finished`` payload)."""

    text: str
    artifacts: list[ChatResultArtifact] = Field(default_factory=list)
    primary_artifact_index: int | None = 0
    usage: Usage | None = None

    @property
    def primary_artifact(self) -> ChatResultArtifact | None:
        if not self.artifacts:
            return None
        if self.primary_artifact_index is None:
            return None
        if self.primary_artifact_index < 0 or self.primary_artifact_index >= len(self.artifacts):
            return None
        return self.artifacts[self.primary_artifact_index]
