"""Python side of the browser output-pane wire contract."""

from __future__ import annotations

from typing import Literal, Required, TypedDict

from tabulaflow.output.specs import ChoiceParameter, NumberParameter, OutputSpec, ParameterSpec

ViewKind = Literal["message", "map", "chart", "data", "query", "graph"]
VIEW_KINDS: tuple[ViewKind, ...] = ("message", "map", "chart", "data", "query", "graph")
CARD_ID_PREFIX = "card_"
PaneSource = Literal["manual"]
ColumnRole = Literal["text", "number", "bool", "media"]
MessageStatus = Literal["error", "not_applicable", "no_result"]


class PaneCard(TypedDict):
    id: str
    artifact_id: str
    label: str | None
    views: list[ViewKind]


class PaneControlChoice(TypedDict):
    id: str
    label: str


class PaneChoiceControl(TypedDict):
    kind: Literal["choice"]
    id: str
    label: str
    choices: list[PaneControlChoice]


class PaneNumberControl(TypedDict):
    kind: Literal["number"]
    id: str
    label: str
    min: float
    max: float
    step: float
    default: float
    unit: str | None


PaneControl = PaneChoiceControl | PaneNumberControl


class PanePanel(TypedDict):
    controls: list[PaneControl]
    default_selection: dict[str, str | int | float | bool]


class PaneTurn(TypedDict, total=False):
    id: int
    title: Required[str]
    cards: Required[list[PaneCard]]
    user: str
    assistant: str
    assistantCodeBlocks: list["CodeData"]
    source: PaneSource
    panel: PanePanel


class PendingPaneTurn(TypedDict):
    id: int
    status: Literal["pending"]
    title: str
    user: str


class ColumnDesc(TypedDict, total=False):
    title: Required[str]
    field: Required[str]
    role: Required[ColumnRole]


class MediaCell(TypedDict):
    kind: Literal["media"]
    mime: str
    src: str
    size: int


class MediaListCell(TypedDict):
    kind: Literal["media-list"]
    items: list[MediaCell | str]


class TableData(TypedDict, total=False):
    maxHeight: int | None
    displayCap: int
    meta: str
    numRows: int
    numCols: int
    truncatedRows: int
    maxRows: int


class DatasetData(TypedDict):
    rows: Required[list[dict[str, object]]]
    columns: Required[list[ColumnDesc]]


class ChartData(TypedDict):
    spec: dict[str, object]
    renderer: str
    wrapClass: str


class CodeData(TypedDict):
    code: str
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
    groupDomain: list[str]


class MessageData(TypedDict):
    status: MessageStatus
    text: str


class MessageCardData(TypedDict):
    message: MessageData


class TableCardData(TypedDict):
    dataset: DatasetData
    table: TableData


class ChartCardData(TypedDict):
    chart: ChartData


class QueryCardData(TypedDict):
    query: CodeData


class MapCardData(TypedDict):
    map: MapData
    datasets: dict[str, DatasetData]


class GraphCardData(TypedDict):
    graph: GraphData


class CardData(TypedDict, total=False):
    message: MessageData
    table: TableData
    dataset: DatasetData
    chart: ChartData
    query: CodeData
    map: MapData
    graph: GraphData
    datasets: dict[str, DatasetData]


def card_payload(*, card_id: str, label: str | None, views: list[ViewKind], artifact_id: str | None = None) -> PaneCard:
    """Build one result card descriptor for the pane."""
    return {"id": card_id, "artifact_id": artifact_id or card_id, "label": label, "views": views}


def turn_payload(
    *,
    title: str,
    cards: list[PaneCard],
    user: str | None = None,
    assistant: str | None = None,
    source: PaneSource | None = None,
    panel: PanePanel | None = None,
) -> PaneTurn:
    """Build one output-pane turn."""
    turn: PaneTurn = {"title": title, "cards": cards}
    if user is not None:
        turn["user"] = user
    if assistant is not None:
        turn["assistant"] = assistant
    if source is not None:
        turn["source"] = source
    if panel is not None:
        turn["panel"] = panel
    return turn


def pane_control(parameter: ParameterSpec) -> PaneControl:
    """Project one output parameter to the browser-pane JSON contract."""
    if isinstance(parameter, ChoiceParameter):
        return {
            "kind": "choice",
            "id": parameter.id,
            "label": parameter.label,
            "choices": [{"id": choice.id, "label": choice.label} for choice in parameter.choices],
        }
    if isinstance(parameter, NumberParameter):
        return {
            "kind": "number",
            "id": parameter.id,
            "label": parameter.label,
            "min": parameter.min,
            "max": parameter.max,
            "step": parameter.step,
            "default": parameter.default,
            "unit": parameter.unit,
        }
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def pane_panel_for_output(output: OutputSpec) -> PanePanel | None:
    """Build the browser-pane control panel for an output."""
    parameters = output.parameters
    if not parameters:
        return None
    parameter_ids = {parameter.id for parameter in parameters}
    return {
        "controls": [pane_control(parameter) for parameter in parameters],
        "default_selection": {key: value for key, value in output.default_selection.items() if key in parameter_ids},
    }


def manual_card_turn(card: PaneCard, *, title: str | None = None) -> PaneTurn:
    """Wrap an already-written card-data payload as a manual pane turn."""
    return turn_payload(title=title or card["label"] or "preview", source="manual", cards=[card])
