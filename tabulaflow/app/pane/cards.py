"""Compose output results into structured browser-pane data."""

from __future__ import annotations

import secrets
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Protocol

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.style import Style as PygmentsStyle
from pygments.util import ClassNotFound

from tabulaflow.app.pane.types import CARD_ID_PREFIX, CodeData, PaneCard, QueryCardData, ViewKind, card_payload
from tabulaflow.app.pane.charts import build_chart_data
from tabulaflow.app.pane.graphs import build_graph_result_data
from tabulaflow.app.pane.maps import build_map_data
from tabulaflow.app.pane.tables import PANE_TABLE_MAX_HEIGHT, _build_table_data
from tabulaflow.app.theme import CODE_TEXT, TabulaflowPygmentsStyle, normalize_query_lexer
from tabulaflow.core.outputs import ChartView, GraphViewSpec, MapView, TableView
from tabulaflow.core.utils import write_strict_json
from tabulaflow.toolhub.output_resolver import ResolvedOutput
from tabulaflow.toolhub.output_store import OutputStore
from tabulaflow.toolhub.render_graph import GraphSpecError, materialize_graph_view

if TYPE_CHECKING:
    import pandas as pd

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


class ResultMetadataLike(Protocol):
    """The tabbed-card payload: a result (``chart_spec`` None) or a chart
    artifact carrying its source result's data and query."""

    df: "pd.DataFrame | None"
    chart_spec: dict[str, object] | None
    query: str | None
    label: str | None
    query_lexer: str


class MapArtifactLike(Protocol):
    map_id: str
    label: str | None
    map_spec: dict[str, object]
    sources: "dict[str, pd.DataFrame]"


class GraphArtifactLike(Protocol):
    graph_id: str
    label: str | None
    graph: object
    layout: str


def build_query_data(sql: str, *, lexer: str = "sql") -> QueryCardData:
    """Build a structured query payload for the browser pane."""
    return {"query": build_code_data(sql, lexer=lexer, fallback_lexer="sql")}


def render_result_data(metadata: ResultMetadataLike, pane_dir: Path) -> PaneCard | None:
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
    if df is not None and not df.empty:
        table_build = _build_table_data(
            df,
            asset_stem=card_id,
            output_dir=pane_dir,
            max_height=PANE_TABLE_MAX_HEIGHT,
        )
        card_data.update(table_build.data)
        if metadata.chart_spec is not None:
            card_data.update(build_chart_data(df, metadata.chart_spec, field_by_column=table_build.field_by_column))
            views.append("chart")
        views.append("data")
    if metadata.query:
        card_data.update(build_query_data(metadata.query, lexer=metadata.query_lexer or "sql"))
        views.append("query")
    if not views:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    write_strict_json(pane_dir / f"{card_id}.data.json", card_data)
    return card_payload(card_id=card_id, label=metadata.label, views=views)


def render_map_data(map_artifact: MapArtifactLike, pane_dir: Path) -> PaneCard | None:
    """Render a standalone map card's payload to JSON; return a pane manifest.

    A map-only card (no chart/data/query views) assembled from one or more query
    results: each source DataFrame becomes a bundled dataset, and each layer reads
    from its ``source`` dataset. Returns ``None`` when no valid layer resolves.
    """
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    sources_payload: dict[str, dict[str, object]] = {}
    for source_id, df in map_artifact.sources.items():
        if df is None or df.empty:
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
    map_data = build_map_data(map_artifact.map_spec, sources_payload)
    if map_data is None:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    write_strict_json(pane_dir / f"{card_id}.data.json", map_data)
    return card_payload(card_id=card_id, label=map_artifact.label, views=["map"])


def render_graph_data(graph_artifact: GraphArtifactLike, pane_dir: Path) -> PaneCard | None:
    """Render a standalone graph card's payload to JSON; return a pane manifest."""
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    graph_data = build_graph_result_data(graph_artifact.graph)
    if graph_data is None:
        return None
    graph_data["graph"]["layout"] = (
        graph_artifact.layout if graph_artifact.layout in {"force", "layered", "tree"} else "force"
    )
    pane_dir.mkdir(parents=True, exist_ok=True)
    write_strict_json(pane_dir / f"{card_id}.data.json", graph_data)
    return card_payload(card_id=card_id, label=graph_artifact.label, views=["graph"])



async def render_resolved_output(resolved_output: ResolvedOutput, output_store: OutputStore, pane_dir: Path) -> list[PaneCard]:
    """Render a resolved output spec to pane card descriptors."""
    cards: list[PaneCard] = []
    for artifact in resolved_output.artifacts:
        view = artifact.view
        try:
            if isinstance(view, TableView):
                payload = await output_store.get_payload(artifact.metadata_by_source[view.source].id)
                card = render_result_data(
                    SimpleNamespace(
                        df=payload.df,
                        chart_spec=None,
                        graph=payload.graph,
                        query=payload.metadata.query,
                        label=artifact.label,
                        query_lexer="cypher" if payload.metadata.connector_type == "property_graph" else "sql",
                    ),
                    pane_dir,
                )
            elif isinstance(view, ChartView):
                payload = await output_store.get_payload(artifact.metadata_by_source[view.source].id)
                card = render_result_data(
                    SimpleNamespace(
                        df=payload.df,
                        chart_spec=view.spec,
                        graph=payload.graph,
                        query=payload.metadata.query,
                        label=artifact.label,
                        query_lexer="cypher" if payload.metadata.connector_type == "property_graph" else "sql",
                    ),
                    pane_dir,
                )
            elif isinstance(view, MapView):
                sources = {}
                for source_id, metadata in artifact.metadata_by_source.items():
                    payload = await output_store.get_payload(metadata.id)
                    if payload.df is not None:
                        sources[source_id] = payload.df
                card = render_map_data(SimpleNamespace(map_id=artifact.artifact_id, label=artifact.label, map_spec=view.spec, sources=sources), pane_dir)
            elif isinstance(view, GraphViewSpec):
                sources = {}
                for source_id, metadata in artifact.metadata_by_source.items():
                    payload = await output_store.get_payload(metadata.id)
                    if payload.df is not None:
                        sources[source_id] = payload.df
                try:
                    graph = materialize_graph_view(view.spec, sources)
                except GraphSpecError:
                    card = None
                else:
                    layout = view.spec.get("layout")
                    card = render_graph_data(
                        SimpleNamespace(
                            graph_id=artifact.artifact_id,
                            label=artifact.label,
                            graph=graph,
                            layout=layout if layout in {"force", "layered", "tree"} else "force",
                        ),
                        pane_dir,
                    )
            else:
                card = None
        except Exception:
            card = None
        if card is not None:
            cards.append(card)
    return cards
