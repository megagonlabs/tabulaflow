"""Rich renderers for CLI output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

import pandas as pd


def print_banner(console: Console, *, model: str, agent: str) -> None:
    """Print the welcome banner."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold]Interactive SQL Chat[/bold]\n"
            f"[dim]model:[/dim] {model}  [dim]agent:[/dim] {agent}\n"
            f"[dim]Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit[/dim]",
            title="[bold cyan]mintq[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()


def render_sql(console: Console, sql: str) -> None:
    """Render a SQL query with syntax highlighting."""
    syntax = Syntax(sql.strip(), "sql", theme="monokai", padding=1)
    console.print(Panel(syntax, title="[bold yellow]SQL[/bold yellow]", border_style="yellow"))


def render_table(console: Console, df: pd.DataFrame, max_rows: int = 50) -> None:
    """Render a DataFrame as a Rich table."""
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    for col in df.columns:
        table.add_column(str(col))

    display_df = df.head(max_rows)
    for _, row in display_df.iterrows():
        table.add_row(*(str(v) for v in row))

    if len(df) > max_rows:
        table.caption = f"[dim]Showing {max_rows} of {len(df)} rows[/dim]"

    console.print(table)


def render_nl(console: Console, text: str) -> None:
    """Render a natural language answer."""
    from rich.markdown import Markdown

    console.print(Panel(Markdown(text), title="[bold green]Answer[/bold green]", border_style="green"))


def render_chart(console: Console, df: pd.DataFrame) -> None:
    """Render a simple auto-detected chart using plotext."""
    import plotext as plt

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        console.print("[dim]No numeric columns to chart.[/dim]")
        return

    plt.clear_figure()
    plt.theme("dark")

    if len(numeric_cols) == 1:
        values = df[numeric_cols[0]].tolist()
        labels = [str(v) for v in df.iloc[:, 0].tolist()] if df.shape[1] > 1 else None
        plt.bar(labels or list(range(len(values))), values)
        plt.title(numeric_cols[0])
    else:
        x = df[numeric_cols[0]].tolist()
        y = df[numeric_cols[1]].tolist()
        plt.scatter(x, y)
        plt.xlabel(numeric_cols[0])
        plt.ylabel(numeric_cols[1])

    chart_str = plt.build()
    console.print(Panel(chart_str, title="[bold blue]Chart[/bold blue]", border_style="blue"))
