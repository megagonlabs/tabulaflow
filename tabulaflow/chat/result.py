"""The chat-turn result view-model — the ``Finished`` event payload.

Pydantic models (consistent with the rest of the data layer in ``core.types`` /
``research.types``), so the whole chat⇄frontend contract is wire-serializable.
The DataFrame field reuses the same Arrow serializer as ``core.ExecResult``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.types import Usage


class ChatResultRecord(BaseModel):
    """Display-ready data for one referenced query result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    record_id: str
    label: str | None
    query: str | None
    df: pd.DataFrame | None
    chart_spec: dict[str, Any] | None
    map_spec: dict[str, Any] | None = None
    query_lexer: str = "sql"

    @field_serializer("df", when_used="always")
    def _serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def _deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)


class ChatResult(BaseModel):
    """The complete result of a single chat turn (the ``Finished`` payload)."""

    text: str
    records: list[ChatResultRecord] = Field(default_factory=list)
    primary_record_index: int | None = 0
    usage: Usage | None = None

    @property
    def primary_record(self) -> ChatResultRecord | None:
        if not self.records:
            return None
        if self.primary_record_index is None:
            return None
        if self.primary_record_index < 0 or self.primary_record_index >= len(self.records):
            return None
        return self.records[self.primary_record_index]
