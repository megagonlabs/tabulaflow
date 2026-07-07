"""Typed payload helpers for the browser output pane."""

from __future__ import annotations

from typing import Literal, Required, TypedDict

ViewKind = Literal["map", "chart", "data", "query", "graph"]
VIEW_KINDS: tuple[ViewKind, ...] = ("map", "chart", "data", "query", "graph")
CARD_ID_PREFIX = "rec_"
PaneSource = Literal["manual"]
ColumnRole = Literal["text", "number", "bool", "media"]


class PaneCard(TypedDict):
    id: str
    label: str | None
    views: list[ViewKind]


class PaneTurn(TypedDict, total=False):
    id: int
    title: Required[str]
    cards: Required[list[PaneCard]]
    user: str
    assistant: str
    source: PaneSource


class ColumnDesc(TypedDict, total=False):
    title: Required[str]
    field: Required[str]
    role: Required[ColumnRole]


class TableData(TypedDict, total=False):
    columns: Required[list[ColumnDesc]]
    hasMedia: bool
    maxHeight: int | None
    displayCap: int
    meta: str
    numRows: int
    numCols: int
    truncatedRows: int
    maxRows: int


class DatasetData(TypedDict, total=False):
    rows: Required[list[dict[str, object]]]
    columns: list[ColumnDesc]


class ChartData(TypedDict):
    spec: dict[str, object]
    renderer: str
    wrapClass: str


class QueryData(TypedDict):
    sql: str
    lexer: str
    language: str
    html: str


class MapData(TypedDict, total=False):
    provider: Required[str]
    layers: Required[list[dict[str, object]]]
    view: dict[str, object]


class GraphData(TypedDict, total=False):
    layout: Required[str]
    elements: Required[dict[str, list[dict[str, object]]]]
    meta: dict[str, object]


class TableCardData(TypedDict):
    dataset: DatasetData
    table: TableData


class ChartCardData(TypedDict):
    chart: ChartData


class QueryCardData(TypedDict):
    query: QueryData


class MapCardData(TypedDict):
    map: MapData
    datasets: dict[str, DatasetData]


class GraphCardData(TypedDict):
    graph: GraphData


class CardData(TypedDict, total=False):
    table: TableData
    dataset: DatasetData
    chart: ChartData
    query: QueryData
    map: MapData
    graph: GraphData
    datasets: dict[str, DatasetData]


def card_payload(*, card_id: str, label: str | None, views: list[ViewKind]) -> PaneCard:
    """Build one result card descriptor for the pane."""
    return {"id": card_id, "label": label, "views": views}


def turn_payload(
    *,
    title: str,
    cards: list[PaneCard],
    user: str | None = None,
    assistant: str | None = None,
    source: PaneSource | None = None,
) -> PaneTurn:
    """Build one output-pane turn."""
    turn: PaneTurn = {"title": title, "cards": cards}
    if user is not None:
        turn["user"] = user
    if assistant is not None:
        turn["assistant"] = assistant
    if source is not None:
        turn["source"] = source
    return turn


def manual_card_turn(card: PaneCard, *, title: str | None = None) -> PaneTurn:
    """Wrap an already-written card-data payload as a manual pane turn."""
    return turn_payload(title=title or card["label"] or "preview", source="manual", cards=[card])
