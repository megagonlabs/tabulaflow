"""Rich renderers for CLI output."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table, box
from rich.text import Text
from rich.theme import Theme

from mintq.cli.theme import ACCENT, ACCENT_BOLD

MINTQ_THEME = Theme({
    "markdown.item.bullet": Style(bold=True),
    "markdown.item.number": Style(bold=True),
    "markdown.code": Style(bold=True, color="white", bgcolor="grey11"),
    "markdown.code_block": Style(color="white", bgcolor="grey11"),
    "markdown.block_quote": Style(color=ACCENT),
    "markdown.list": Style(color=ACCENT),
})

if TYPE_CHECKING:
    import pandas as pd
    from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema


_LOGO = """\
 ███╗   ███╗ ██╗ ███╗   ██╗ ████████╗  ██████╗
 ████╗ ████║ ██║ ████╗  ██║ ╚══██╔══╝ ██╔═══██╗
 ██╔████╔██║ ██║ ██╔██╗ ██║    ██║    ██║   ██║
 ██║╚██╔╝██║ ██║ ██║╚██╗██║    ██║    ██║▄▄ ██║
 ██║ ╚═╝ ██║ ██║ ██║ ╚████║    ██║    ╚██████╔╝
 ╚═╝     ╚═╝ ╚═╝ ╚═╝  ╚═══╝    ╚═╝     ╚══▀▀═╝"""


def print_banner(console: Console, *, model: str, agent: str) -> None:
    """Print the welcome banner."""
    console.print()
    console.print(Text(_LOGO, style=ACCENT_BOLD))
    console.print()
    console.print(
        Panel.fit(
            f"[bold]Interactive SQL Chat[/bold]\n"
            f"[dim]model:[/dim] {model}\n"
            f"[dim]Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to exit[/dim]",
            border_style=ACCENT,
        )
    )
    console.print()


def render_sql(console: Console, sql: str) -> None:
    """Render a SQL query with syntax highlighting."""
    syntax = Syntax(
        sql.strip(), "sql", theme="solarized-dark",
        padding=(1, 1), line_numbers=True,
        background_color="default",
    )
    console.print(syntax)


def render_table(console: Console, df: pd.DataFrame, max_rows: int = 10) -> None:
    """Render a DataFrame as a Rich table."""
    table = Table(show_header=True, header_style=ACCENT_BOLD, show_lines=True)
    for col in df.columns:
        table.add_column(str(col))

    truncated = len(df) > max_rows
    display_df = df.head(max_rows)
    for _, row in display_df.iterrows():
        table.add_row(*(str(v) for v in row))

    if truncated:
        table.add_row(*["[dim]...[/dim]"] * len(df.columns))
        table.caption = f"[dim]{len(df)} rows total (truncated)[/dim]"

    console.print(table)


def render_nl(console: Console, text: str) -> None:
    """Render a natural language answer."""
    from rich.markdown import Markdown

    console.push_theme(MINTQ_THEME)
    layout = Table(show_header=False, show_edge=False, box=None, padding=0, expand=True)
    layout.add_column(width=2, no_wrap=True, vertical="top")
    layout.add_column(ratio=1)
    layout.add_row(Text("◆", style=ACCENT_BOLD), Markdown(text))
    console.print(layout)
    console.pop_theme()


def render_chart(console: Console, df: pd.DataFrame, vegalite_spec: dict) -> None:
    """Render a plotext chart from a Vega-Lite spec and DataFrame."""
    from mintq.toolhub.render_chart import parse_vegalite_spec, render_plotext

    try:
        mark, x_field, y_field, title = parse_vegalite_spec(vegalite_spec)
        chart_str = render_plotext(mark, x_field, y_field, title, df, console.width)
        console.print(Text.from_ansi(chart_str))
    except Exception as e:
        console.print(f"[dim]Chart error: {e}[/dim]")


# ---------------------------------------------------------------------------
# Schema rendering
# ---------------------------------------------------------------------------


def _qualified_name(tbl: SQLTableSchema) -> str:
    """Return schema.table if schema_name is set, otherwise just table."""
    if tbl.schema_name:
        return f"{tbl.schema_name}.{tbl.name}"
    return tbl.name


def _is_multi_schema(schema: SQLSchema) -> bool:
    """True if tables span more than one distinct schema namespace."""
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
    """Build a borderless table of table names, rows, cols, description."""
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


def render_schema_overview(console: Console, schema: SQLSchema, alias: str) -> None:
    """Render database-level schema overview."""
    multi = _is_multi_schema(schema)
    total_cols = schema.num_total_columns()
    dialect = schema.dialect or ""
    subtitle = ", ".join(
        s for s in [dialect, f"{len(schema.tables)} tables", f"{total_cols} columns"] if s
    )

    if multi:
        grouped: dict[str | None, list[SQLTableSchema]] = defaultdict(list)
        for tbl in schema.tables:
            grouped[tbl.schema_name].append(tbl)

        parts: list[Panel] = []
        for schema_name, tables in sorted(grouped.items(), key=lambda kv: kv[0] or ""):
            section_title = (
                f"[bold]{alias}[/bold].[{ACCENT_BOLD}]{schema_name}[/{ACCENT_BOLD}]"
                if schema_name
                else f"[bold]{alias}[/bold]"
            )
            inner = _build_overview_table(tables)
            parts.append(Panel(inner, title=section_title, border_style=ACCENT))

        for p in parts:
            console.print(p)
        console.print(f"  [dim]{subtitle}[/dim]")
    else:
        title = f"[bold]{alias}[/bold]"
        inner = _build_overview_table(schema.tables)
        footer = Text(subtitle, style="dim")
        console.print(Panel(Group(inner, footer), title=title, border_style=ACCENT))


def render_table_detail(console: Console, tbl: SQLTableSchema, multi_schema: bool = False) -> None:
    """Render column-level detail for a single table inside a panel."""
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

    console.print(Panel(Group(*parts), title=title, border_style=ACCENT))


def render_column_detail(console: Console, tbl: SQLTableSchema, col: SQLColumnSchema) -> None:
    """Render full metadata for a single column."""
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

    fk_refs = [fk for fk in col.foreign_keys]
    for fk in fk_refs:
        tgt = f"{fk.foreign_schema_name}.{fk.foreign_table}" if fk.foreign_schema_name else fk.foreign_table
        lines.append(f"[bold]FK →[/bold]         {tgt}({', '.join(fk.foreign_columns)})")

    body = "\n".join(lines)
    console.print(Panel(body, title=f"[bold]{display}.{col.name}[/bold]", border_style=ACCENT))


def resolve_table(
    schema: SQLSchema, name: str
) -> SQLTableSchema | list[SQLTableSchema] | None:
    """Resolve a table name, supporting optional schema.table syntax.

    Returns:
        A single table on exact/unambiguous match, a list if ambiguous across
        schemas, or None if not found.
    """
    schema_part: str | None = None
    table_part: str = name
    if "." in name:
        schema_part, table_part = name.rsplit(".", 1)

    exact: list[SQLTableSchema] = []
    ci_matches: list[SQLTableSchema] = []

    for tbl in schema.tables:
        if schema_part is not None:
            schema_match = (
                tbl.schema_name == schema_part
                or (tbl.schema_name is not None and tbl.schema_name.lower() == schema_part.lower())
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


def render_agent_progress(console: Console) -> object:
    """Create a progress display for streaming agent execution."""
    from mintq.cli.agent import AgentProgressDisplay

    return AgentProgressDisplay(console)


# ---------------------------------------------------------------------------
# Result viewer — Tab/Shift+Tab cycling between NL / SQL / Table views
# ---------------------------------------------------------------------------

_VIEW_NAMES = ["response", "chart", "data", "sql"]


def _capture_rich(console: Console, render_fn: object, *args: object) -> str:
    """Render a Rich callable to an ANSI string."""
    from io import StringIO

    buf = StringIO()
    capture_console = Console(file=buf, force_terminal=True, width=console.width, theme=MINTQ_THEME)
    render_fn(capture_console, *args)  # type: ignore[operator]
    return buf.getvalue()


async def view_result(console: Console, result: object) -> None:
    """Launch an interactive viewer to cycle through NL / SQL / Table views."""
    from mintq.cli.agent import ChatResult

    assert isinstance(result, ChatResult)

    views: dict[str, str | None] = {}
    if result.text:
        views["response"] = _capture_rich(console, render_nl, result.text)
    if result.chart_spec is not None and result.chart_df is not None:
        views["chart"] = _capture_rich(console, render_chart, result.chart_df, result.chart_spec)
    if result.df is not None and not result.df.empty:
        views["data"] = _capture_rich(console, render_table, result.df)
    if result.sql:
        views["sql"] = _capture_rich(console, render_sql, result.sql)

    available = [v for v in _VIEW_NAMES if v in views]
    if not available:
        console.print("[dim]No results to display.[/dim]")
        return

    if len(available) == 1:
        console.print(Text.from_ansi(views[available[0]]), end="")
        return

    from prompt_toolkit.application import Application
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl

    current_idx = [0]

    def _render_tab_bar() -> str:
        from io import StringIO as _StringIO

        buf = _StringIO()
        bar_console = Console(file=buf, force_terminal=True, width=console.width)
        parts = Text()
        for i, name in enumerate(available):
            if i > 0:
                parts.append("  ")
            if i == current_idx[0]:
                parts.append(f" {name} ", style=f"bold white on {ACCENT}")
            else:
                parts.append(f" {name} ")
        parts.append("    ")
        parts.append("←/→: switch  Enter: done", style="italic dim")
        bar_console.print(parts)
        return buf.getvalue()

    def _get_content() -> ANSI:
        view_key = available[current_idx[0]]
        content = views[view_key] or ""
        tab_bar = _render_tab_bar()
        return ANSI(content + "\n" + tab_bar)

    kb = KeyBindings()

    @kb.add("tab")
    @kb.add("right")
    def _next(event: object) -> None:
        current_idx[0] = (current_idx[0] + 1) % len(available)
        app.invalidate()

    @kb.add("s-tab")
    @kb.add("left")
    def _prev(event: object) -> None:
        current_idx[0] = (current_idx[0] - 1) % len(available)
        app.invalidate()

    @kb.add("enter")
    @kb.add("q")
    @kb.add("escape")
    def _exit(event: object) -> None:
        event.app.exit()  # type: ignore[union-attr]

    content_control = FormattedTextControl(
        text=_get_content,
        focusable=False,
        show_cursor=False,
    )

    layout = Layout(
        HSplit([
            Window(content=content_control, wrap_lines=True),
        ])
    )

    app: Application[None] = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,
        erase_when_done=True,
    )

    await app.run_async()

    view_key = available[current_idx[0]]
    console.print(Text.from_ansi(views[view_key] or ""))
