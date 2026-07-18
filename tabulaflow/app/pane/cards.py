"""Compose a cited result record into structured browser-pane data."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from tabulaflow.app.pane.types import CARD_ID_PREFIX, PaneCard, QueryCardData, ViewKind, card_payload
from tabulaflow.app.pane.charts import build_chart_data
from tabulaflow.app.pane.graphs import build_graph_data
from tabulaflow.app.pane.maps import build_map_data
from tabulaflow.app.pane.tables import PANE_TABLE_MAX_HEIGHT, _build_table_data
from tabulaflow.app.theme import TabulaflowPygmentsStyle, normalize_query_lexer

if TYPE_CHECKING:
    import pandas as pd


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
    graph_spec: dict[str, object]
    sources: "dict[str, pd.DataFrame]"


def build_query_data(sql: str, *, lexer: str = "sql") -> QueryCardData:
    """Build a structured query payload for the browser pane."""
    resolved_lexer = normalize_query_lexer(lexer)
    try:
        lex = get_lexer_by_name(resolved_lexer)
    except ClassNotFound:
        resolved_lexer = "sql"
        lex = get_lexer_by_name("sql")
    highlighted = highlight(sql, lex, HtmlFormatter(style=TabulaflowPygmentsStyle, noclasses=True))
    language = lex.name or resolved_lexer.upper()
    return {"query": {"sql": sql, "lexer": resolved_lexer, "language": language, "html": highlighted}}


def render_record_data(record: ResultRecordLike, pane_dir: Path) -> PaneCard | None:
    """Render a record or chart artifact's payload to JSON; return a pane manifest.

    The descriptor is ordered chart -> data -> query, including only the views
    the artifact has, or ``None`` when it has nothing displayable.
    """
    views: list[ViewKind] = []
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    record_data: dict[str, object] = {}
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
    (pane_dir / f"{card_id}.data.json").write_text(
        json.dumps(record_data, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
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
    (pane_dir / f"{card_id}.data.json").write_text(
        json.dumps(map_data, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return card_payload(card_id=card_id, label=map_record.label, views=["map"])


def render_graph_data(graph_record: GraphArtifactLike, pane_dir: Path) -> PaneCard | None:
    """Render a standalone graph card's payload to JSON; return a pane manifest."""
    card_id = f"{CARD_ID_PREFIX}{secrets.token_hex(6)}"
    sources_payload: dict[str, dict[str, object]] = {}
    for source_id, df in graph_record.sources.items():
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
    graph_data = build_graph_data(graph_record.graph_spec, sources_payload)
    if graph_data is None:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    (pane_dir / f"{card_id}.data.json").write_text(
        json.dumps(graph_data, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return card_payload(card_id=card_id, label=graph_record.label, views=["graph"])
