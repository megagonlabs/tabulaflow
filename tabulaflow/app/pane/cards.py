"""Compose a cited result record into structured browser-pane data."""

from __future__ import annotations

import secrets
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Protocol, cast

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
from tabulaflow.core.utils import write_strict_json

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


class ResultRecordLike(Protocol):
    """The tabbed-card payload: a query record (``chart_spec`` None) or a chart
    artifact carrying its source record's data and query."""

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


def render_record_data(record: ResultRecordLike, pane_dir: Path) -> PaneCard | None:
    """Render a record or chart artifact's payload to JSON; return a pane manifest.

    The descriptor is ordered chart -> data -> query, including only the views
    the artifact has, or ``None`` when it has nothing displayable.
    """
    views: list[ViewKind] = []
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    record_data: dict[str, object] = {}
    graph = getattr(record, "graph", None)
    if graph is not None:
        graph_data = build_graph_result_data(graph)
        if graph_data is not None:
            record_data.update(graph_data)
            views.append("graph")
    df = record.df
    if df is not None and not df.empty:
        table_build = _build_table_data(
            df,
            asset_stem=card_id,
            output_dir=pane_dir,
            max_height=PANE_TABLE_MAX_HEIGHT,
        )
        record_data.update(table_build.data)
        if record.chart_spec is not None:
            record_data.update(build_chart_data(df, record.chart_spec, field_by_column=table_build.field_by_column))
            views.append("chart")
        views.append("data")
    if record.query:
        record_data.update(build_query_data(record.query, lexer=record.query_lexer or "sql"))
        views.append("query")
    if not views:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    write_strict_json(pane_dir / f"{card_id}.data.json", record_data)
    return card_payload(card_id=card_id, label=record.label, views=views)


def render_map_data(map_record: MapArtifactLike, pane_dir: Path) -> PaneCard | None:
    """Render a standalone map card's payload to JSON; return a pane manifest.

    A map-only card (no chart/data/query views) assembled from one or more query
    results: each source DataFrame becomes a bundled dataset, and each layer reads
    from its ``source`` dataset. Returns ``None`` when no valid layer resolves.
    """
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    sources_payload: dict[str, dict[str, object]] = {}
    for source_id, df in map_record.sources.items():
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
    map_data = build_map_data(map_record.map_spec, sources_payload)
    if map_data is None:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    write_strict_json(pane_dir / f"{card_id}.data.json", map_data)
    return card_payload(card_id=card_id, label=map_record.label, views=["map"])


def render_graph_data(graph_record: GraphArtifactLike, pane_dir: Path) -> PaneCard | None:
    """Render a standalone graph card's payload to JSON; return a pane manifest."""
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    graph_data = build_graph_result_data(graph_record.graph)
    if graph_data is None:
        return None
    graph_data["graph"]["layout"] = (
        graph_record.layout if graph_record.layout in {"force", "layered", "tree"} else "force"
    )
    pane_dir.mkdir(parents=True, exist_ok=True)
    write_strict_json(pane_dir / f"{card_id}.data.json", graph_data)
    return card_payload(card_id=card_id, label=graph_record.label, views=["graph"])



async def render_resolved_output(resolved_output: object, output_store: object, pane_dir: Path) -> list[PaneCard]:
    """Render a resolved output spec to pane card descriptors."""
    from tabulaflow.core.outputs import ChartView, GraphArtifactView, MapView, TableView
    from tabulaflow.toolhub.output_runtime import ResolvedOutput
    from tabulaflow.toolhub.output_store import OutputStore
    from tabulaflow.toolhub.render_graph import GraphSpecError, materialize_graph_view

    assert isinstance(resolved_output, ResolvedOutput)
    cards: list[PaneCard] = []
    for artifact in resolved_output.artifacts:
        view = artifact.view
        try:
            if isinstance(view, TableView):
                payload = await cast(OutputStore, output_store).get_payload(artifact.results_by_source[view.source].id)
                card = render_record_data(
                    SimpleNamespace(
                        df=payload.df,
                        chart_spec=None,
                        graph=payload.graph,
                        query=payload.record.query,
                        label=artifact.label,
                        query_lexer="cypher" if payload.record.connector_type == "property_graph" else "sql",
                    ),
                    pane_dir,
                )
            elif isinstance(view, ChartView):
                payload = await cast(OutputStore, output_store).get_payload(artifact.results_by_source[view.source].id)
                card = render_record_data(
                    SimpleNamespace(
                        df=payload.df,
                        chart_spec=view.spec,
                        graph=payload.graph,
                        query=payload.record.query,
                        label=artifact.label,
                        query_lexer="cypher" if payload.record.connector_type == "property_graph" else "sql",
                    ),
                    pane_dir,
                )
            elif isinstance(view, MapView):
                sources = {}
                for source_id, record in artifact.results_by_source.items():
                    payload = await cast(OutputStore, output_store).get_payload(record.id)
                    if payload.df is not None:
                        sources[source_id] = payload.df
                card = render_map_data(SimpleNamespace(map_id=artifact.artifact_id, label=artifact.label, map_spec=view.spec, sources=sources), pane_dir)
            elif isinstance(view, GraphArtifactView):
                sources = {}
                for source_id, record in artifact.results_by_source.items():
                    payload = await cast(OutputStore, output_store).get_payload(record.id)
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
