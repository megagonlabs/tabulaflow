"""Rich renderable builders and CLI display helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.align import Align
from rich.columns import Columns
from rich.console import Group
from rich.markup import escape as _rich_escape
from rich.panel import Panel
from rich.style import Style
from rich import box
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from tabulaflow.app.theme import (
    ACCENT,
    ACCENT_BOLD,
    ACCENT_DIM,
    ACCENT_RGB,
    CODE_TEXT,
    ERROR,
    KEY_HINT,
    TABULAFLOW_RICH_SYNTAX_THEME,
    normalize_query_lexer,
)

TABULAFLOW_THEME = Theme(
    {
        "markdown.item.bullet": Style(bold=True),
        "markdown.item.number": Style(bold=True),
        "markdown.code": Style(bold=True, color=CODE_TEXT, bgcolor="grey11"),
        "markdown.code_block": Style(color=CODE_TEXT, bgcolor="grey11"),
        "markdown.block_quote": Style(color=ACCENT),
        "markdown.list": Style(color=ACCENT),
    }
)

DATA_PREVIEW_MAX_ROWS = 5
DATA_PREVIEW_MAX_COLUMNS = 10
QUERY_PREVIEW_MAX_LINES = 7

if TYPE_CHECKING:
    import pandas as pd
    from rich.console import RenderableType


def build_query(
    query: str,
    max_lines: int | None = QUERY_PREVIEW_MAX_LINES,
    *,
    lexer: str = "sql",
    line_numbers: bool = False,
) -> RenderableType:
    """Build a syntax-highlighted query renderable."""
    stripped = query.strip()
    all_lines = stripped.splitlines()
    total_lines = len(all_lines)
    truncated = max_lines is not None and total_lines > max_lines
    if truncated:
        assert max_lines is not None
        omitted_lines = total_lines - max_lines
        display_query = "\n".join(all_lines[:max_lines]) + f"\n... ({omitted_lines} lines omitted)"
    else:
        display_query = stripped
    syntax = Syntax(
        display_query,
        normalize_query_lexer(lexer),
        theme=TABULAFLOW_RICH_SYNTAX_THEME,
        padding=(1, 2),
        line_numbers=line_numbers,
        background_color="default",
    )
    # Trailing blank row so the bottom-hint ("↑↓ Prev/Next result · ↵ Inspect")
    # has visual breathing room from the syntax block. The other views
    # already get this gap from their own footer (data) or chart axes.
    return Group(syntax, Text(""))


# Per-column overhead in a box.SQUARE table with default padding (0, 1):
# 1 right border + 2 horizontal padding cells. Plus one leftmost border for the table.
_COL_OVERHEAD = 3
_TABLE_BORDER = 1
_MIN_CELL_WIDTH = 8


def compute_preview_layout(
    n_total_cols: int,
    available_width: int,
    max_columns: int = DATA_PREVIEW_MAX_COLUMNS,
) -> tuple[int, int]:
    """Decide how many columns to show and how wide each cell should be.

    Drops trailing columns when even minimum-width cells would overflow the
    available width, then distributes leftover space evenly across the kept
    columns. Always returns at least one shown column when the dataframe has
    any, even if the result will technically overflow — Rich will clip it
    rather than producing border-only "ghost" columns.
    """
    capped = min(n_total_cols, max_columns)
    if capped <= 0:
        return 0, _MIN_CELL_WIDTH
    n_fit = (available_width - _TABLE_BORDER) // (_MIN_CELL_WIDTH + _COL_OVERHEAD)
    n_show = max(1, min(capped, n_fit))
    usable = available_width - _TABLE_BORDER - n_show * _COL_OVERHEAD
    cell_width = max(_MIN_CELL_WIDTH, usable // n_show)
    return n_show, cell_width


def data_preview_caption(
    df: pd.DataFrame,
    max_rows: int,
    shown_cols: int,
) -> str:
    """Return the 'showing N of M ...' caption for a truncated preview, or empty."""
    parts: list[str] = []
    if len(df) > max_rows:
        parts.append(f"showing {max_rows} of {len(df)} rows")
    if len(df.columns) > shown_cols:
        parts.append(f"showing {shown_cols} of {len(df.columns)} columns")
    return " | ".join(parts)


def build_table(
    df: pd.DataFrame,
    available_width: int = 80,
    max_rows: int = DATA_PREVIEW_MAX_ROWS,
    max_columns: int = DATA_PREVIEW_MAX_COLUMNS,
    action_hint: str | None = None,
    include_footer: bool = True,
) -> tuple[RenderableType, int]:
    """Build a DataFrame preview as a Rich renderable.

    Returns (renderable, shown_cols). ``shown_cols`` is the number of columns
    actually rendered after width-aware dropping — callers use it to keep the
    truncation caption in sync with what the user sees.

    When ``include_footer`` is False, the renderable is just the table; the
    caller is responsible for rendering the caption / action_hint elsewhere.
    """
    n_show, cell_width = compute_preview_layout(len(df.columns), available_width, max_columns)
    display_columns = list(df.columns[:n_show])

    table = Table(
        show_header=True,
        header_style=ACCENT_BOLD,
        show_lines=False,
        box=box.SQUARE,
    )
    for col in display_columns:
        table.add_column(str(col), no_wrap=True, max_width=cell_width, overflow="ellipsis")

    display_df = df.loc[:, display_columns].head(max_rows)
    for _, row in display_df.iterrows():
        table.add_row(*(_format_table_cell(v) for v in row))

    if not include_footer:
        return table, n_show

    stats_text = data_preview_caption(df, max_rows, n_show)
    if not stats_text and not action_hint:
        return table, n_show

    footer: Columns | Text
    if action_hint:
        left = Text(f"[ {action_hint} ]", style=KEY_HINT)
        right = Text(stats_text, style="dim") if stats_text else Text("")
        footer = Columns([left, Align.right(right)], expand=True, equal=False)
    else:
        footer = Text(stats_text, style="dim")
    return Group(table, footer), n_show


_PREVIEW_CELL_TRUNCATE = 500


def _format_table_cell(value: object) -> str:
    """Normalize cell text to a single line; column-level max_width handles truncation.

    Escapes Rich markup metacharacters so binary blobs (e.g. ``str(bytes)``
    repr containing ``[/...]`` patterns) don't blow up the markup parser
    with ``MarkupError: closing tag ... doesn't match any open tag``.

    Short-circuits binary cells to a compact ``<binary: N bytes>`` placeholder.
    ``str(<bytes>)`` of even a single ~1 MB BLOB produces a multi-MB escaped
    hex string; Rich's column-measure pass then walks that whole string per
    cell, stalling view-switch by seconds on tables with image/audio/video
    columns. The visible cell is ellipsized anyway — no information loss.

    Truncates very long text cells before the replace/escape passes for the
    same reason: a 5 MB string would have ``.replace()`` walked over it 3
    times and ``_rich_escape`` once, plus Rich's table-render measure pass
    per cell. The visible cell is only ~30 chars wide, so anything past
    ``_PREVIEW_CELL_TRUNCATE`` is invisible.
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<binary: {len(value):,} bytes>"
    # HuggingFace Image/Audio struct: ``{"bytes": <blob>, "path": ...}``
    if isinstance(value, dict):
        inner = value.get("bytes")
        if isinstance(inner, (bytes, bytearray, memoryview)):
            return f"<binary: {len(inner):,} bytes>"
    s = str(value)
    if len(s) > _PREVIEW_CELL_TRUNCATE:
        s = s[:_PREVIEW_CELL_TRUNCATE] + "…"
    # Normalize whitespace to single spaces — collapses newlines (which
    # Rich otherwise renders as hard line breaks, expanding the row),
    # tabs, and runs of spaces. ``" ".join(s.split())`` is the idiomatic
    # one-pass form; full multi-line content stays available via Enter.
    s = " ".join(s.split())
    return _rich_escape(s)


def _spec_title(spec: dict[str, object]) -> str:
    """Extract a Vega-Lite spec's title text (``""`` if absent)."""
    title = spec.get("title", "") if isinstance(spec, dict) else ""
    if isinstance(title, dict):
        title = title.get("text", "")
    return str(title) if title else ""


def _build_chart_card(spec: dict[str, object], *, height: int | None) -> RenderableType:
    """Placeholder box for charts plotext can't draw faithfully (open in browser).

    A dim rounded box with the title, chart type, and an explanatory line, all
    centered. Full-screen (``height`` set) fills the chart region and centers
    vertically; the inline result preview (``height`` is None) sizes to content.
    """
    from tabulaflow.toolhub.render_chart import chart_type_label

    type_label = chart_type_label(spec)
    title = _spec_title(spec)
    lines: list[RenderableType] = [Text(title or type_label, style="dim bold", justify="center")]
    if title:
        lines.append(Text(type_label, style="dim", justify="center"))
    lines.append(Text(""))
    lines.append(Text("Open the browser pane to view this chart.", style="dim", justify="center"))
    group = Group(*lines)
    body = Align.center(group, vertical="middle") if height is not None else group
    return Panel(body, height=height, box=box.ROUNDED, border_style=ACCENT_DIM, padding=(1, 2))


def build_chart(
    df: pd.DataFrame, vegalite_spec: dict[str, object], width: int = 80, height: int | None = None
) -> RenderableType:
    """Build a chart renderable from a Vega-Lite spec and DataFrame.

    Simple x/y specs render inline via plotext; anything richer (color/facet/
    transform/multi-view or an unsupported mark) returns a card directing the
    user to open it in the browser, rather than a misleading approximation.
    """
    from tabulaflow.toolhub.render_chart import (
        ChartNotRenderable,
        is_plotext_renderable,
        parse_vegalite_spec,
        render_plotext,
    )

    if not is_plotext_renderable(vegalite_spec):
        return _build_chart_card(vegalite_spec, height=height)
    try:
        mark, x_field, y_field, title = parse_vegalite_spec(vegalite_spec)
        chart_str = render_plotext(mark, x_field, y_field, title, df, width, height, color=ACCENT_RGB)
        return Text.from_ansi(chart_str)
    except ChartNotRenderable:
        # Structurally fine, but the data can't be drawn faithfully in a terminal
        # (no numeric measure axis) — degrade to the "open in browser" card.
        return _build_chart_card(vegalite_spec, height=height)
    except Exception as e:
        return Text.from_markup(f"[{ERROR}]Chart error:[/] {e}")


# ---------------------------------------------------------------------------
# Result view building — used by TUI widgets
# ---------------------------------------------------------------------------


VIEW_KIND_CHART = "Chart"
VIEW_KIND_DATA = "Data"
VIEW_KIND_QUERY = "Query"
VIEW_KIND_MAP = "Map"
VIEW_KIND_GRAPH = "Graph"
VIEW_KIND_INFO = "Info"


def _build_map_card(map_spec: dict[str, object]) -> RenderableType:
    """Placeholder box for a map (rendered in the browser, not the terminal).

    Mirrors :func:`_build_chart_card`: a dim rounded box with the map's title/type
    and a line directing the user to the browser pane.
    """
    from tabulaflow.toolhub.render_map import map_type_label

    type_label = map_type_label(map_spec)
    title = map_spec.get("title") if isinstance(map_spec, dict) else None
    heading = str(title) if isinstance(title, str) and title.strip() else type_label
    lines: list[RenderableType] = [Text(heading, style="dim bold", justify="center")]
    if isinstance(title, str) and title.strip():
        lines.append(Text(type_label, style="dim", justify="center"))
    lines.append(Text(""))
    lines.append(Text("Open the browser pane to view this map.", style="dim", justify="center"))
    return Panel(Group(*lines), box=box.ROUNDED, border_style=ACCENT_DIM, padding=(1, 2))


def _build_graph_card() -> RenderableType:
    """Placeholder box for a graph (rendered in the browser, not the terminal)."""
    heading = "Network graph"
    lines: list[RenderableType] = [Text(heading, style="dim bold", justify="center")]
    lines.append(Text(""))
    lines.append(Text("Open the browser pane to view this graph.", style="dim", justify="center"))
    return Panel(Group(*lines), box=box.ROUNDED, border_style=ACCENT_DIM, padding=(1, 2))


def _build_info_card(message: str) -> RenderableType:
    """Simple informational card body, used for panel combinations without rows."""
    return Panel(Text(message, style="dim", justify="center"), box=box.ROUNDED, border_style=ACCENT_DIM, padding=(1, 2))


@dataclass
class ViewItem:
    """A single view (Chart/Data/Query) belonging to one result."""

    kind: str
    renderable: RenderableType
    # Populated only for the matching kind; others are None.
    chart_spec: dict[str, object] | None = None
    data_shape: tuple[int, int] | None = None  # (num_rows, num_cols)
    shown_cols: int | None = None  # columns actually rendered in the preview
    query: tuple[str, str] | None = None  # (raw_query, lexer)


@dataclass
class CardGroup:
    """Display-ready views for one artifact, ordered Chart -> Data -> Query."""

    label: str
    artifact_id: str
    # The result backing the Data/Chart views (the table artifact itself,
    # or the chart's source); ``None`` for maps and graphs.
    source_result_id: str | None = None
    views: list[ViewItem] = field(default_factory=list)


def build_artifact_card_views(
    artifacts: Sequence[object], width: int = 80, *, release_dataframes: bool = True
) -> list[CardGroup]:
    """Build card groups from legacy/debug display payload objects."""
    groups: list[CardGroup] = []
    used_labels: set[str] = set()
    for artifact in artifacts:
        base_label = getattr(artifact, "label", None) or "result"
        label = _unique_record_label(base_label, used_labels)
        used_labels.add(label)
        kind = getattr(artifact, "kind", None)
        if kind == "placeholder":
            groups.append(
                CardGroup(
                    label=label,
                    artifact_id=f"placeholder:{label}",
                    views=[ViewItem(kind=VIEW_KIND_INFO, renderable=_build_info_card(str(getattr(artifact, "message", ""))))],
                )
            )
            continue
        if kind == "map":
            groups.append(
                CardGroup(
                    label=label,
                    artifact_id=str(getattr(artifact, "map_id")),
                    views=[ViewItem(kind=VIEW_KIND_MAP, renderable=_build_map_card(getattr(artifact, "map_spec")))],
                )
            )
            continue
        if kind == "graph":
            groups.append(
                CardGroup(
                    label=label,
                    artifact_id=str(getattr(artifact, "graph_id")),
                    views=[ViewItem(kind=VIEW_KIND_GRAPH, renderable=_build_graph_card())],
                )
            )
            continue
        chart_spec = getattr(artifact, "chart_spec", None)
        artifact_id = str(getattr(artifact, "chart_id", getattr(artifact, "record_id", "result")))
        record_id = str(getattr(artifact, "record_id", artifact_id))
        views: list[ViewItem] = []
        if getattr(artifact, "graph", None) is not None:
            views.append(ViewItem(kind=VIEW_KIND_GRAPH, renderable=_build_graph_card()))
        df = getattr(artifact, "df", None)
        if chart_spec is not None and df is not None:
            views.append(ViewItem(kind=VIEW_KIND_CHART, renderable=build_chart(df, chart_spec, width), chart_spec=chart_spec))
        if df is not None and not df.empty:
            renderable, shown_cols = build_table(df, available_width=width, include_footer=False)
            views.append(
                ViewItem(
                    kind=VIEW_KIND_DATA,
                    renderable=renderable,
                    data_shape=(len(df), len(df.columns)),
                    shown_cols=shown_cols,
                )
            )
        query = getattr(artifact, "query", None)
        query_lexer = getattr(artifact, "query_lexer", "sql")
        if query:
            views.append(ViewItem(kind=VIEW_KIND_QUERY, renderable=build_query(query, lexer=query_lexer), query=(query, query_lexer)))
        if views:
            groups.append(CardGroup(label=label, artifact_id=artifact_id, source_result_id=record_id, views=views))
    if release_dataframes:
        for artifact in artifacts:
            if hasattr(artifact, "df"):
                artifact.df = None
            if hasattr(artifact, "sources"):
                artifact.sources = {}
    return groups


async def build_resolved_output_card_views(
    resolved_output: object,
    output_store: object,
    width: int = 80,
) -> list[CardGroup]:
    """Build display cards directly from a resolved output spec."""
    from typing import cast

    from tabulaflow.core.outputs import ChartView, GraphViewSpec, MapView, TableView
    from tabulaflow.toolhub.output_resolver import ResolvedOutput
    from tabulaflow.toolhub.output_store import OutputStore
    from tabulaflow.toolhub.render_graph import GraphSpecError, materialize_graph_view

    assert isinstance(resolved_output, ResolvedOutput)
    store = cast(OutputStore, output_store)
    groups: list[CardGroup] = []
    used_labels: set[str] = set()
    for artifact in resolved_output.artifacts:
        base_label = artifact.label or "result"
        label = _unique_record_label(base_label, used_labels)
        used_labels.add(label)
        view = artifact.view
        if isinstance(view, TableView):
            payload = await store.get_payload(artifact.metadata_by_source[view.source].id)
            group = _card_group_from_payload(label, artifact.artifact_id, payload, width)
            if group is not None:
                groups.append(group)
        elif isinstance(view, ChartView):
            payload = await store.get_payload(artifact.metadata_by_source[view.source].id)
            group = _card_group_from_payload(label, artifact.artifact_id, payload, width, chart_spec=view.spec)
            if group is not None:
                groups.append(group)
        elif isinstance(view, MapView):
            groups.append(
                CardGroup(
                    label=label,
                    artifact_id=artifact.artifact_id,
                    views=[ViewItem(kind=VIEW_KIND_MAP, renderable=_build_map_card(view.spec))],
                )
            )
        elif isinstance(view, GraphViewSpec):
            graph_sources = {}
            for source_id, metadata in artifact.metadata_by_source.items():
                payload = await store.get_payload(metadata.id)
                if payload.df is not None:
                    graph_sources[source_id] = payload.df
            try:
                materialize_graph_view(view.spec, graph_sources)
            except GraphSpecError:
                continue
            groups.append(
                CardGroup(
                    label=label,
                    artifact_id=artifact.artifact_id,
                    views=[ViewItem(kind=VIEW_KIND_GRAPH, renderable=_build_graph_card())],
                )
            )
    return groups


def _card_group_from_payload(
    label: str,
    artifact_id: str,
    payload: object,
    width: int,
    chart_spec: dict[str, object] | None = None,
) -> CardGroup | None:
    from tabulaflow.toolhub.output_store import ResultPayload

    assert isinstance(payload, ResultPayload)
    views: list[ViewItem] = []
    if payload.graph is not None:
        views.append(ViewItem(kind=VIEW_KIND_GRAPH, renderable=_build_graph_card()))
    if chart_spec is not None and payload.df is not None:
        views.append(ViewItem(kind=VIEW_KIND_CHART, renderable=build_chart(payload.df, chart_spec, width), chart_spec=chart_spec))
    if payload.df is not None and not payload.df.empty:
        renderable, shown_cols = build_table(payload.df, available_width=width, include_footer=False)
        views.append(
            ViewItem(
                kind=VIEW_KIND_DATA,
                renderable=renderable,
                data_shape=(len(payload.df), len(payload.df.columns)),
                shown_cols=shown_cols,
            )
        )
    if payload.metadata.query:
        lexer = "cypher" if payload.metadata.connector_type == "property_graph" else "sql"
        views.append(
            ViewItem(
                kind=VIEW_KIND_QUERY,
                renderable=build_query(payload.metadata.query, lexer=lexer),
                query=(payload.metadata.query, lexer),
            )
        )
    if not views:
        return None
    return CardGroup(label=label, artifact_id=artifact_id, source_result_id=payload.metadata.id, views=views)


def _unique_record_label(base_label: str, used: set[str]) -> str:
    """Return a unique label suitable for view names."""
    if base_label not in used:
        return base_label
    i = 2
    while True:
        candidate = f"{base_label}_{i}"
        if candidate not in used:
            return candidate
        i += 1
