"""Serializable definitions for artifacts shown in answers."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class TableArtifactDef(BaseModel):
    """Logical table artifact, resolved from a query source."""

    kind: Literal["table"] = "table"
    source_id: str
    label: str | None = None


class ChartArtifactDef(BaseModel):
    """Logical chart artifact, resolved from a query source and Vega-Lite spec."""

    kind: Literal["chart"] = "chart"
    chart_id: str
    source_id: str
    chart_spec: dict[str, Any]
    label: str | None = None


class MapArtifactDef(BaseModel):
    """Logical map artifact."""

    kind: Literal["map"] = "map"
    map_id: str
    map_spec: dict[str, Any]
    label: str | None = None


class GraphArtifactDef(BaseModel):
    """Logical graph artifact."""

    kind: Literal["graph"] = "graph"
    graph_id: str
    graph_spec: dict[str, Any]
    label: str | None = None


ArtifactDef = Annotated[
    TableArtifactDef | ChartArtifactDef | MapArtifactDef | GraphArtifactDef,
    Field(discriminator="kind"),
]
