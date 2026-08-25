"""Compose output results into structured browser-pane data."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping
from typing import TYPE_CHECKING

import pandas as pd
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.style import Style as PygmentsStyle
from pygments.util import ClassNotFound

from tabulaflow.app.pane.types import (
    CARD_ID_PREFIX,
    CodeData,
    MessageStatus,
    PaneCard,
    QueryCardData,
    ViewKind,
    card_payload,
)
from tabulaflow.app.pane.charts import build_chart_data
from tabulaflow.app.pane.graphs import build_graph_result_data
from tabulaflow.app.pane.maps import build_map_data
from tabulaflow.app.pane.tables import PANE_TABLE_MAX_HEIGHT, _build_table_data
from tabulaflow.app.theme import CODE_TEXT, TabulaflowPygmentsStyle, normalize_query_lexer
from tabulaflow.core.serialization import dumps_strict_json
from tabulaflow.output.resolver import (
    ResolvedChartArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedOutput,
    ResolvedTableArtifact,
    UnavailableArtifact,
)

if TYPE_CHECKING:
    import pandas as pd


def _write_strict_json(path: Path, data: object) -> None:
    path.write_text(dumps_strict_json(data), encoding="utf-8")


PANE_CODE_TEXT = "#E0E0E0"


class PanePygmentsStyle(PygmentsStyle):  # type: ignore[misc]
    """Pygments style for browser-pane query cards."""

    background_color = TabulaflowPygmentsStyle.background_color
    styles = {
        token: PANE_CODE_TEXT if style == CODE_TEXT else style
        for token, style in TabulaflowPygmentsStyle.styles.items()
    }


def build_code_data(code: str, *, lexer: str = "text", fallback_lexer: str = "text") -> CodeData:
    """Build a highlighted browser-pane code payload."""
    resolved_lexer = normalize_query_lexer(lexer)
    try:
        lex = get_lexer_by_name(resolved_lexer)
    except ClassNotFound:
        resolved_lexer = fallback_lexer
        lex = get_lexer_by_name(fallback_lexer)
    highlighted = highlight(code, lex, HtmlFormatter(style=PanePygmentsStyle, noclasses=True))
    language = lex.name or resolved_lexer.upper()
    return {"code": code, "lexer": resolved_lexer, "language": language, "html": highlighted}


@dataclass(frozen=True)
class ResultCardInput:
    """Input for a browser-pane result card."""

    df: "pd.DataFrame | None"
    label: str | None
    chart_spec: Mapping[str, object] | None = None
    graph: object | None = None
    query: str | None = None
    query_lexer: str = "sql"


@dataclass(frozen=True)
class MapCardInput:
    """Input for a browser-pane map card."""

    label: str | None
    spec: Mapping[str, object]
    sources: "dict[str, pd.DataFrame]"


@dataclass(frozen=True)
class GraphCardInput:
    """Input for a browser-pane graph card."""

    label: str | None
    graph: object
    layout: str = "force"


@dataclass(frozen=True)
class MessageCardInput:
    """Input for a browser-pane message card."""

    label: str | None
    text: str
    status: MessageStatus = "not_applicable"


def build_query_data(sql: str, *, lexer: str = "sql") -> QueryCardData:
    """Build a structured query payload for the browser pane."""
    return {"query": build_code_data(sql, lexer=lexer, fallback_lexer="sql")}


def render_result_data(metadata: ResultCardInput, pane_dir: Path, *, artifact_id: str | None = None) -> PaneCard | None:
    """Render a result or chart artifact's payload to JSON; return a pane manifest.

    The descriptor is ordered chart -> data -> query, including only the views
    the artifact has, or ``None`` when it has nothing displayable.
    """
    views: list[ViewKind] = []
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    card_data: dict[str, object] = {}
    graph = getattr(metadata, "graph", None)
    if graph is not None:
        graph_data = build_graph_result_data(graph)
        if graph_data is not None:
            card_data.update(graph_data)
            views.append("graph")
    df = metadata.df
    if df is not None:
        table_build = _build_table_data(
            df,
            asset_stem=card_id,
            output_dir=pane_dir,
            max_height=PANE_TABLE_MAX_HEIGHT,
        )
        card_data.update(table_build.data)
        if metadata.chart_spec is not None:
            card_data.update(
                build_chart_data(df, dict(metadata.chart_spec), field_by_column=table_build.field_by_column)
            )
            views.append("chart")
        views.append("data")
    if metadata.query:
        card_data.update(build_query_data(metadata.query, lexer=metadata.query_lexer or "sql"))
        views.append("query")
    if not views:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    _write_strict_json(pane_dir / f"{card_id}.data.json", card_data)
    return card_payload(card_id=card_id, artifact_id=artifact_id, label=metadata.label, views=views)


def render_map_data(map_artifact: MapCardInput, pane_dir: Path, *, artifact_id: str | None = None) -> PaneCard | None:
    """Render a standalone map card's payload to JSON; return a pane manifest.

    A map-only card (no chart/data/query views) assembled from one or more query
    results: each source DataFrame becomes a bundled dataset, and each layer reads
    from its ``source`` dataset. Returns ``None`` when no valid layer resolves.
    """
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    sources_payload: dict[str, dict[str, object]] = {}
    for source_id, df in map_artifact.sources.items():
        if df is None:
            continue
        table_build = _build_table_data(
            df,
            asset_stem=f"{card_id}_{source_id}",
            output_dir=pane_dir,
            max_height=None,
        )
        dataset = table_build.data.get("dataset")
        table_payload = table_build.data.get("table")
        sources_payload[source_id] = {
            "rows": dataset.get("rows", []) if isinstance(dataset, dict) else [],
            "columns": table_payload.get("columns", []) if isinstance(table_payload, dict) else [],
            "field_by_column": table_build.field_by_column,
        }
    map_data = build_map_data(map_artifact.spec, sources_payload)
    if map_data is None:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    _write_strict_json(pane_dir / f"{card_id}.data.json", map_data)
    return card_payload(card_id=card_id, artifact_id=artifact_id, label=map_artifact.label, views=["map"])


def render_graph_data(
    graph_artifact: GraphCardInput, pane_dir: Path, *, artifact_id: str | None = None
) -> PaneCard | None:
    """Render a standalone graph card's payload to JSON; return a pane manifest."""
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    graph_data = build_graph_result_data(graph_artifact.graph)
    if graph_data is None:
        return None
    graph_data["graph"]["layout"] = (
        graph_artifact.layout if graph_artifact.layout in {"force", "layered", "tree"} else "force"
    )
    pane_dir.mkdir(parents=True, exist_ok=True)
    _write_strict_json(pane_dir / f"{card_id}.data.json", graph_data)
    return card_payload(card_id=card_id, artifact_id=artifact_id, label=graph_artifact.label, views=["graph"])


def render_message_data(message: MessageCardInput, pane_dir: Path, *, artifact_id: str | None = None) -> PaneCard:
    """Render a standalone message card's payload to JSON; return a pane manifest."""
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    pane_dir.mkdir(parents=True, exist_ok=True)
    _write_strict_json(
        pane_dir / f"{card_id}.data.json",
        {"message": {"status": message.status, "text": message.text}},
    )
    return card_payload(card_id=card_id, artifact_id=artifact_id, label=message.label, views=["message"])


async def render_resolved_output(resolved_output: ResolvedOutput, pane_dir: Path) -> list[PaneCard]:
    """Render a resolved output spec to pane card descriptors."""
    cards: list[PaneCard] = []
    for artifact in resolved_output.artifacts:
        if isinstance(artifact, UnavailableArtifact):
            cards.append(
                render_message_data(
                    MessageCardInput(label=artifact.label, text=artifact.reason, status=artifact.status),
                    pane_dir,
                    artifact_id=artifact.artifact_id,
                )
            )
            continue
        try:
            if isinstance(artifact, ResolvedTableArtifact):
                payload = artifact.payload
                card = render_result_data(
                    ResultCardInput(
                        df=payload.df,
                        chart_spec=None,
                        graph=payload.graph,
                        query=payload.metadata.query,
                        label=artifact.label,
                        query_lexer="cypher" if payload.metadata.connector_type == "property_graph" else "sql",
                    ),
                    pane_dir,
                    artifact_id=artifact.artifact_id,
                )
            elif isinstance(artifact, ResolvedChartArtifact):
                payload = artifact.payload
                card = render_result_data(
                    ResultCardInput(
                        df=payload.df,
                        chart_spec=artifact.spec,
                        graph=payload.graph,
                        query=payload.metadata.query,
                        label=artifact.label,
                        query_lexer="cypher" if payload.metadata.connector_type == "property_graph" else "sql",
                    ),
                    pane_dir,
                    artifact_id=artifact.artifact_id,
                )
            elif isinstance(artifact, ResolvedMapArtifact):
                sources = {}
                for source_id, payload in artifact.payload_by_source.items():
                    if payload.df is not None:
                        sources[source_id] = payload.df
                card = render_map_data(
                    MapCardInput(label=artifact.label, spec=artifact.spec, sources=sources),
                    pane_dir,
                    artifact_id=artifact.artifact_id,
                )
            elif isinstance(artifact, ResolvedGraphArtifact):
                card = render_graph_data(
                    GraphCardInput(label=artifact.label, graph=artifact.graph, layout=artifact.layout),
                    pane_dir,
                    artifact_id=artifact.artifact_id,
                )
            else:
                card = None
        except Exception:
            card = None
        if card is not None:
            cards.append(card)
    return cards
