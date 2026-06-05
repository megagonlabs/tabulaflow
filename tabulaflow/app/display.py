"""Rich renderable builders and CLI display helpers."""

from __future__ import annotations

from collections import defaultdict
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

from tabulaflow.app.theme import ACCENT, ACCENT_BOLD, ACCENT_RGB, KEY_HINT

TABULAFLOW_THEME = Theme(
    {
        "markdown.item.bullet": Style(bold=True),
        "markdown.item.number": Style(bold=True),
        "markdown.code": Style(bold=True, color="white", bgcolor="grey11"),
        "markdown.code_block": Style(color="white", bgcolor="grey11"),
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

    from tabulaflow.core.types import (
        NodeSchema,
        PropertyGraphSchema,
        RelationshipSchema,
        SQLColumnSchema,
        SQLSchema,
        SQLTableSchema,
    )


_LOGO = """\
 ███╗   ███╗ ██╗ ███╗   ██╗ ████████╗  ██████╗
 ████╗ ████║ ██║ ████╗  ██║ ╚══██╔══╝ ██╔═══██╗
 ██╔████╔██║ ██║ ██╔██╗ ██║    ██║    ██║   ██║
 ██║╚██╔╝██║ ██║ ██║╚██╗██║    ██║    ██║▄▄ ██║
 ██║ ╚═╝ ██║ ██║ ██║ ╚████║    ██║    ╚██████╔╝
 ╚═╝     ╚═╝ ╚═╝ ╚═╝  ╚═══╝    ╚═╝     ╚══▀▀═╝"""


def build_banner(*, model: str) -> RenderableType:
    """Build the welcome banner as a Rich renderable."""
    return Group(
        Text(_LOGO, style=ACCENT_BOLD),
        Text(),
        Panel.fit(
            f"[dim]model:[/dim] {model}\n[dim]Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to exit[/dim]",
            border_style=ACCENT,
        ),
    )


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
        lexer,
        theme="dracula",
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


def build_chart(
    df: pd.DataFrame, vegalite_spec: dict[str, object], width: int = 80, height: int | None = None
) -> RenderableType:
    """Build a plotext chart renderable from a Vega-Lite spec and DataFrame."""
    from tabulaflow.toolhub.render_chart import parse_vegalite_spec, render_plotext

    try:
        mark, x_field, y_field, title = parse_vegalite_spec(vegalite_spec)
        chart_str = render_plotext(mark, x_field, y_field, title, df, width, height, color=ACCENT_RGB)
        return Text.from_ansi(chart_str)
    except Exception as e:
        return Text.from_markup(f"[red]Chart error:[/red] {e}")


# ---------------------------------------------------------------------------
# Result view building — used by TUI widgets
# ---------------------------------------------------------------------------


VIEW_KIND_CHART = "Chart"
VIEW_KIND_DATA = "Data"
VIEW_KIND_QUERY = "Query"


@dataclass
class ViewItem:
    """A single view (Chart/Data/Query) belonging to one record."""

    kind: str
    renderable: RenderableType
    # Populated only for the matching kind; others are None.
    chart_spec: dict[str, object] | None = None
    data_shape: tuple[int, int] | None = None  # (num_rows, num_cols)
    shown_cols: int | None = None  # columns actually rendered in the preview
    query: tuple[str, str] | None = None  # (raw_query, lexer)


@dataclass
class RecordGroup:
    """Display-ready views for one record, ordered Chart -> Data -> Query."""

    label: str
    record_id: str
    views: list[ViewItem] = field(default_factory=list)


def build_result_views(result: object, width: int = 80) -> list[RecordGroup]:
    """Build per-record view groups from a ChatResult.

    The returned list preserves record order; within each record, views are
    ordered Chart -> Data -> Query and absent kinds are omitted. Records with
    no views at all are dropped.
    """
    from tabulaflow.chat import ChatResult

    assert isinstance(result, ChatResult)

    groups: list[RecordGroup] = []
    used_labels: set[str] = set()
    for record in result.records:
        base_label = record.label or "result"
        label = _unique_record_label(base_label, used_labels)
        used_labels.add(label)

        views: list[ViewItem] = []
        if record.chart_spec is not None and record.df is not None:
            views.append(
                ViewItem(
                    kind=VIEW_KIND_CHART,
                    renderable=build_chart(record.df, record.chart_spec, width),
                    chart_spec=record.chart_spec,
                )
            )
        if record.df is not None and not record.df.empty:
            renderable, shown_cols = build_table(record.df, available_width=width, include_footer=False)
            views.append(
                ViewItem(
                    kind=VIEW_KIND_DATA,
                    renderable=renderable,
                    data_shape=(len(record.df), len(record.df.columns)),
                    shown_cols=shown_cols,
                )
            )
        if record.query:
            views.append(
                ViewItem(
                    kind=VIEW_KIND_QUERY,
                    renderable=build_query(record.query, lexer=record.query_lexer),
                    query=(record.query, record.query_lexer),
                )
            )

        if views:
            groups.append(RecordGroup(label=label, record_id=record.record_id, views=views))

    # Release DF references — previews have been rendered to Rich renderables.
    for record in result.records:
        record.df = None

    return groups


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


# ---------------------------------------------------------------------------
# Schema rendering
# ---------------------------------------------------------------------------


def _qualified_name(tbl: SQLTableSchema) -> str:
    if tbl.schema_name:
        return f"{tbl.schema_name}.{tbl.name}"
    return tbl.name


def _is_multi_schema(schema: SQLSchema) -> bool:
    schemas = {t.schema_name for t in schema.tables}
    schemas.discard(None)
    return len(schemas) > 1


def _display_name(tbl: SQLTableSchema, multi_schema: bool) -> str:
    if multi_schema and tbl.schema_name:
        return f"{tbl.schema_name}.{tbl.name}"
    return tbl.name


def _format_rows(n: int | None) -> str:
    if n is None:
        return ""
    return f"{n:,}"


def _build_overview_table(tables: list[SQLTableSchema]) -> Table:
    inner = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=ACCENT_BOLD, padding=(0, 2))
    inner.add_column("Table")
    inner.add_column("Rows", justify="right")
    inner.add_column("Cols", justify="right")
    inner.add_column("Description", max_width=50)

    for tbl in tables:
        inner.add_row(
            tbl.name,
            _format_rows(tbl.num_rows),
            str(len(tbl.columns)),
            (tbl.description or "")[:50],
        )
    return inner


def build_schema_overview(schema: SQLSchema, alias: str) -> RenderableType:
    """Build database-level schema overview renderable."""
    multi = _is_multi_schema(schema)
    total_cols = schema.num_total_columns()
    dialect = schema.dialect or ""
    subtitle = ", ".join(s for s in [dialect, f"{len(schema.tables)} tables", f"{total_cols} columns"] if s)

    if multi:
        grouped: dict[str | None, list[SQLTableSchema]] = defaultdict(list)
        for tbl in schema.tables:
            grouped[tbl.schema_name].append(tbl)

        parts: list[RenderableType] = []
        for schema_name, tables in sorted(grouped.items(), key=lambda kv: kv[0] or ""):
            section_title = (
                f"[bold]{alias}[/bold].[{ACCENT_BOLD}]{schema_name}[/{ACCENT_BOLD}]"
                if schema_name
                else f"[bold]{alias}[/bold]"
            )
            inner = _build_overview_table(tables)
            parts.append(Panel(inner, title=section_title, border_style=ACCENT))

        parts.append(Text(f"  {subtitle}", style="dim"))
        return Group(*parts)
    else:
        title = f"[bold]{alias}[/bold]"
        inner = _build_overview_table(schema.tables)
        footer = Text(subtitle, style="dim")
        return Panel(Group(inner, footer), title=title, border_style=ACCENT)


def build_table_detail(tbl: SQLTableSchema, multi_schema: bool = False) -> RenderableType:
    """Build column-level detail renderable for a single table."""
    display = _display_name(tbl, multi_schema)
    row_info = f" ({tbl.num_rows:,} rows)" if tbl.num_rows is not None else ""
    title = f"[bold]{display}[/bold][dim]{row_info}[/dim]"

    pk_set = set(tbl.primary_key)
    fk_col_set = {col for fk in tbl.foreign_keys for col in fk.columns}

    inner = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=ACCENT_BOLD, padding=(0, 2))
    inner.add_column("Column")
    inner.add_column("Type")
    inner.add_column("Key", justify="center")
    inner.add_column("Null", justify="center")
    inner.add_column("Examples", max_width=40)

    for col in tbl.columns:
        key_parts: list[str] = []
        if col.name in pk_set:
            key_parts.append("[bold yellow]PK[/bold yellow]")
        if col.name in fk_col_set:
            key_parts.append(f"[{ACCENT}]FK[/{ACCENT}]")
        key = " ".join(key_parts)

        null_str = "[green]✓[/green]" if col.nullable else "[dim]✗[/dim]"

        examples_str = ""
        if col.examples:
            examples_str = ", ".join(str(e) for e in col.examples[:5])
            if len(examples_str) > 40:
                examples_str = examples_str[:37] + "..."

        name_style = "bold" if col.name in pk_set else ""
        name_text = Text(col.name, style=name_style)

        inner.add_row(name_text, col.dtype or "", key, null_str, f"[dim]{examples_str}[/dim]")

    parts: list[Table | Text] = [inner]

    if tbl.foreign_keys:
        fk_text = Text()
        fk_text.append("\n")
        for i, fk in enumerate(tbl.foreign_keys):
            src = ", ".join(fk.columns)
            tgt_table = f"{fk.foreign_schema_name}.{fk.foreign_table}" if fk.foreign_schema_name else fk.foreign_table
            tgt = ", ".join(fk.foreign_columns)
            if i > 0:
                fk_text.append("\n")
            fk_text.append("  FK ", style=ACCENT_BOLD)
            fk_text.append(f"{src} → {tgt_table}({tgt})")
        parts.append(fk_text)

    if tbl.description:
        desc_text = Text()
        desc_text.append("\n  ")
        desc_text.append(tbl.description, style="dim italic")
        parts.append(desc_text)

    return Panel(Group(*parts), title=title, border_style=ACCENT)


def build_column_detail(tbl: SQLTableSchema, col: SQLColumnSchema) -> RenderableType:
    """Build full metadata renderable for a single column."""
    display = _qualified_name(tbl)
    pk_set = set(tbl.primary_key)

    lines: list[str] = []
    lines.append(f"[bold]Type:[/bold]        {col.dtype}")

    if col.name in pk_set:
        pk_label = "composite" if col.primary_key_type == "composite" else "yes"
        lines.append(f"[bold]Primary key:[/bold] {pk_label}")

    null_detail = "yes" if col.nullable else "no"
    if col.null_ratio is not None:
        null_detail += f" ({col.null_ratio:.1%} null)"
    lines.append(f"[bold]Nullable:[/bold]    {null_detail}")

    if col.num_unique is not None:
        unique_detail = f"{col.num_unique:,} values"
        if col.unique_ratio is not None:
            unique_detail += f" ({col.unique_ratio:.1%})"
        lines.append(f"[bold]Unique:[/bold]      {unique_detail}")

    if col.examples:
        ex_str = ", ".join(str(e) for e in col.examples[:8])
        lines.append(f"[bold]Examples:[/bold]    [dim]{ex_str}[/dim]")

    if col.description:
        lines.append(f"[bold]Description:[/bold] {col.description}")

    fk_refs = list(col.foreign_keys)
    for fk in fk_refs:
        tgt = f"{fk.foreign_schema_name}.{fk.foreign_table}" if fk.foreign_schema_name else fk.foreign_table
        lines.append(f"[bold]FK →[/bold]         {tgt}({', '.join(fk.foreign_columns)})")

    body = "\n".join(lines)
    return Panel(body, title=f"[bold]{display}.{col.name}[/bold]", border_style=ACCENT)


def resolve_table(schema: SQLSchema, name: str) -> SQLTableSchema | list[SQLTableSchema] | None:
    """Resolve a table name, supporting optional schema.table syntax."""
    schema_part: str | None = None
    table_part: str = name
    if "." in name:
        schema_part, table_part = name.rsplit(".", 1)

    exact: list[SQLTableSchema] = []
    ci_matches: list[SQLTableSchema] = []

    for tbl in schema.tables:
        if schema_part is not None:
            schema_match = tbl.schema_name == schema_part or (
                tbl.schema_name is not None and tbl.schema_name.lower() == schema_part.lower()
            )
            if not schema_match:
                continue

        if tbl.name == table_part:
            exact.append(tbl)
        elif tbl.name.lower() == table_part.lower():
            ci_matches.append(tbl)

    candidates = exact or ci_matches
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        return candidates
    return None


def resolve_column(tbl: SQLTableSchema, name: str) -> SQLColumnSchema | None:
    """Resolve a column name with case-insensitive fallback."""
    for col in tbl.columns:
        if col.name == name:
            return col
    for col in tbl.columns:
        if col.name.lower() == name.lower():
            return col
    return None


def build_property_graph_overview(schema: PropertyGraphSchema, alias: str) -> RenderableType:
    """Build full property-graph schema renderable."""
    from tabulaflow.core.formatters.cypher import CypherSchemaFormatter

    body = CypherSchemaFormatter().format(schema)
    return Panel(body, title=f"[bold]{alias}[/bold] · cypher", border_style=ACCENT)


def resolve_graph_node_label(schema: PropertyGraphSchema, name: str) -> NodeSchema | None:
    for node in schema.nodes:
        if node.label.lower() == name.lower():
            return node
    return None


def resolve_graph_rel_patterns(schema: PropertyGraphSchema, name: str) -> list[RelationshipSchema]:
    return [r for r in schema.relationships if r.label.lower() == name.lower()]


def build_graph_node_detail(node: NodeSchema) -> RenderableType:
    from tabulaflow.core.formatters.cypher import CypherSchemaFormatter

    fmt = CypherSchemaFormatter()
    return Panel(fmt.format_node(node), title=f"[bold]:{node.label}[/bold]", border_style=ACCENT)


def build_graph_reltype_detail(rel_type: str, patterns: list[RelationshipSchema]) -> RenderableType:
    lines = [f"(:{p.source_label})-[:{p.label}]->(:{p.target_label})" for p in patterns]
    body = "\n".join(lines)
    props_extra = ""
    for p in patterns:
        if p.properties:
            props_extra = "\n\n" + "\n".join(f"  {x.name}: {x.dtype}" for x in p.properties)
            break
    return Panel(
        body + props_extra,
        title=f"[bold]:{rel_type}[/bold] patterns",
        border_style=ACCENT,
    )
