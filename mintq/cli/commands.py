"""Slash-command handlers for the CLI chat."""

from __future__ import annotations

import os
import shlex
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse, urlunparse

from rich.console import Console
from rich.table import Table

from mintq.cli.theme import ACCENT, ACCENT_BOLD

if TYPE_CHECKING:
    from mintq.cli.chat import ChatSession

COMMAND_PREFIX = "/"

_ASYNC_DRIVERS = {"aiosqlite", "asyncmy", "asyncpg"}

_FILE_EXTENSIONS: dict[str, str] = {
    ".sqlite": "sqlite+aiosqlite",
    ".sqlite3": "sqlite+aiosqlite",
    ".db": "sqlite+aiosqlite",
    ".duckdb": "duckdb",
}


def _engine_kwargs_for_url(url: str) -> dict[str, Any]:
    """Build connector engine kwargs based on URL scheme."""
    scheme = url.split("://", 1)[0].split("+", 1)[0].lower()
    if scheme != "bigquery":
        return {}

    google_cloud_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
        "GCP_BILLING_PROJECT"
    )
    if not google_cloud_project:
        raise ValueError(
            "BigQuery billing project required: set GOOGLE_CLOUD_PROJECT (or GCP_BILLING_PROJECT)."
        )

    engine_kwargs: dict[str, Any] = {"billing_project_id": google_cloud_project}
    google_application_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if google_application_credentials:
        engine_kwargs["credentials_path"] = google_application_credentials
    return engine_kwargs


async def handle_command(text: str, session: ChatSession, console: Console) -> bool:
    """Dispatch a slash command. Returns True if the session should quit."""
    parts = shlex.split(text)
    cmd = parts[0].lower()
    args = parts[1:]

    handler = COMMANDS.get(cmd)
    if handler is None:
        console.print(f"[red]Unknown command:[/red] {cmd}. Type [bold]/help[/bold] for available commands.")
        return False

    return await handler(args, session, console)


async def _cmd_help(args: list[str], session: ChatSession, console: Console) -> bool:
    table = Table(title="Commands", show_header=True, header_style=ACCENT_BOLD, show_lines=False)
    table.add_column("Command", style="bold")
    table.add_column("Description")

    for cmd, (_, description) in _COMMAND_HELP.items():
        table.add_row(cmd, description)

    console.print(table)
    return False


async def _cmd_exit(args: list[str], session: ChatSession, console: Console) -> bool:
    await session.connections.disconnect_all()
    return True


async def _cmd_clear(args: list[str], session: ChatSession, console: Console) -> bool:
    console.clear()
    return False


async def _cmd_connect(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print(
            "[red]Usage:[/red] /connect <url_or_path> [alias]\n"
            "[dim]  /connect ./data/schools.sqlite\n"
            "  /connect sqlite+aiosqlite:///path/to/db.sqlite\n"
            "  /connect bigquery://bigquery-public-data/noaa_gsod\n"
            "  /connect snowflake://user@account/db\n"
            "  /connect duckdb:///path/to/db.duckdb[/dim]"
        )
        return False

    raw = args[0]
    url = _normalize_url(raw)
    alias = args[1] if len(args) > 1 else _alias_from_url(url)
    engine_type = _infer_engine_type(url)

    if session.connections.has(alias):
        console.print(
            f"[red]Alias already in use:[/red] {alias}. "
            "Disconnect first or provide a different alias: /connect <url> <alias>"
        )
        return False

    url = await _prompt_password_if_needed(url, console)
    try:
        engine_kwargs = _engine_kwargs_for_url(url)
    except ValueError as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        return False

    from mintq.db_connector.sql_conn import SQLConnector

    global_id = f"cli+{alias}"
    with console.status(f"[dim]Connecting to {alias}...[/dim]", spinner_style=ACCENT):
        try: 
            connector = await SQLConnector.from_url_async(
                global_id=global_id,
                db_name=alias,
                engine_type=engine_type,
                url=url,
                read_only=True,
                enable_schema_caching=True,
                enable_query_caching=False,
                **engine_kwargs,
            )
        except Exception as e:
            console.print(f"[red]Connection failed:[/red] {e}")
            return False

    n_tables = len(connector.schema.tables) if connector.schema else 0
    dialect = connector.language or "unknown"
    session.connections.add(alias, connector)
    console.print(
        f"[{ACCENT}]✓[/{ACCENT}] Connected to [bold]{alias}[/bold] ({dialect}, {n_tables} tables)"
    )
    return False


async def _cmd_disconnect(args: list[str], session: ChatSession, console: Console) -> bool:
    alias = args[0] if args else session.connections.active_alias
    if alias is None:
        console.print("[red]No active connection.[/red]")
        return False
    if await session.connections.remove(alias):
        console.print(f"[{ACCENT}]✓[/{ACCENT}] Disconnected from [bold]{alias}[/bold]")
    else:
        console.print(f"[red]No connection named:[/red] {alias}")
    return False


async def _cmd_databases(args: list[str], session: ChatSession, console: Console) -> bool:
    connections = session.connections.list_all()
    if not connections:
        console.print("[dim]No databases connected. Use /connect <url> to add one.[/dim]")
        return False

    table = Table(show_header=True, header_style=ACCENT_BOLD)
    table.add_column("Alias", style="bold")
    table.add_column("Active")
    table.add_column("Tables")

    for alias, conn in connections.items():
        is_active = "●" if alias == session.connections.active_alias else ""
        n_tables = str(len(conn.schema.tables)) if conn.schema else "?"
        table.add_row(alias, f"[green]{is_active}[/green]", n_tables)

    console.print(table)
    return False


async def _cmd_use(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print("[red]Usage:[/red] /use <alias>")
        return False
    if session.connections.use(args[0]):
        console.print(f"[{ACCENT}]✓[/{ACCENT}] Switched to [bold]{args[0]}[/bold]")
    else:
        console.print(f"[red]No connection named:[/red] {args[0]}")
    return False


async def _cmd_schema(args: list[str], session: ChatSession, console: Console) -> bool:
    from mintq.cli.display import (
        render_schema_overview,
        render_table_detail,
        render_column_detail,
        resolve_table,
        resolve_column,
        _is_multi_schema,
        _display_name,
    )

    conn = session.connections.active_connector
    if conn is None:
        console.print("[red]No active connection.[/red] Use /connect first.")
        return False

    schema = conn.schema
    if schema is None:
        console.print("[dim]Schema not available.[/dim]")
        return False

    multi = _is_multi_schema(schema)
    alias = session.connections.active_alias or ""

    if not args:
        render_schema_overview(console, schema, alias)
        return False

    result = resolve_table(schema, args[0])
    if result is None:
        console.print(f"[red]Table not found:[/red] {args[0]}")
        return False
    if isinstance(result, list):
        console.print(f"[red]Ambiguous table name:[/red] {args[0]}. Matches:")
        for t in result:
            console.print(f"  [dim]{_display_name(t, multi=True)}[/dim]")
        console.print("[dim]Use the qualified name: /schema <schema>.<table>[/dim]")
        return False

    tbl = result

    if len(args) < 2:
        render_table_detail(console, tbl, multi_schema=multi)
        return False

    col = resolve_column(tbl, args[1])
    if col is None:
        console.print(f"[red]Column not found:[/red] {args[1]} in {_display_name(tbl, multi)}")
        return False

    render_column_detail(console, tbl, col)
    return False


async def _cmd_mode(args: list[str], session: ChatSession, console: Console) -> bool:
    valid = {"nl", "sql", "table", "chart", "all"}
    if not args:
        console.print(f"[dim]Active modes:[/dim] {', '.join(sorted(session.output_modes))}")
        console.print(f"[dim]Usage:[/dim] /mode <{'|'.join(sorted(valid))}>")
        return False

    mode = args[0].lower()
    if mode == "all":
        session.output_modes = {"nl", "sql", "table", "chart"}
    elif mode in valid:
        if mode in session.output_modes:
            session.output_modes.discard(mode)
            console.print(f"[yellow]−[/yellow] Disabled [bold]{mode}[/bold]")
        else:
            session.output_modes.add(mode)
            console.print(f"[green]+[/green] Enabled [bold]{mode}[/bold]")
    else:
        console.print(f"[red]Invalid mode:[/red] {mode}. Choose from {', '.join(sorted(valid))}")

    return False


async def _cmd_model(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print(f"[dim]Current model:[/dim] {session.model}")
        return False
    session.model = args[0]
    console.print(f"[{ACCENT}]✓[/{ACCENT}] Model set to [bold]{session.model}[/bold]")
    return False


async def _cmd_agent(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print(f"[dim]Current agent:[/dim] {session.agent_name}")
        return False
    session.agent_name = args[0]
    console.print(f"[{ACCENT}]✓[/{ACCENT}] Agent set to [bold]{session.agent_name}[/bold]")
    return False


def _normalize_url(raw: str) -> str:
    """Expand a bare file path into a SQLAlchemy URL, or return as-is."""
    for ext, scheme in _FILE_EXTENSIONS.items():
        if raw.endswith(ext):
            abspath = os.path.abspath(raw)
            return f"{scheme}:///{abspath}"
    return raw


def _infer_engine_type(url: str) -> Literal["async", "sync"]:
    """Decide async vs sync engine based on the URL scheme/driver."""
    scheme = url.split("://", 1)[0] if "://" in url else url
    parts = scheme.split("+")
    driver = parts[1] if len(parts) > 1 else parts[0]
    if driver in _ASYNC_DRIVERS:
        return "async"
    return "sync"


async def _prompt_password_if_needed(url: str, console: Console) -> str:
    """If URL has a username but no password, prompt interactively."""
    parsed = urlparse(url)
    if parsed.username and not parsed.password and parsed.hostname:
        from prompt_toolkit import prompt as pt_prompt

        console.print(f"[dim]Authenticating as[/dim] [bold]{parsed.username}[/bold]")
        password = await pt_prompt(
            "  Password: ",
            is_password=True,
            async_=True,
        )
        replaced = parsed._replace(
            netloc=f"{parsed.username}:{password}@{parsed.hostname}"
            + (f":{parsed.port}" if parsed.port else "")
        )
        return urlunparse(replaced)
    return url


def _alias_from_url(url: str) -> str:
    """Derive a short alias from a database URL."""
    if ":///" in url:
        path = url.split("///", 1)[-1]
        return os.path.splitext(os.path.basename(path))[0]
    parsed = urlparse(url)
    if parsed.path and parsed.path.strip("/"):
        return parsed.path.strip("/").rsplit("/", 1)[-1]
    if parsed.hostname:
        return parsed.hostname
    return url


async def _cmd_view(args: list[str], session: ChatSession, console: Console) -> bool:
    if session.last_result is None:
        console.print("[dim]No result to display. Ask a question first.[/dim]")
        return False

    from mintq.cli.display import view_result

    await view_result(console, session.last_result)
    return False


async def _cmd_sql(args: list[str], session: ChatSession, console: Console) -> bool:
    if session.last_result is None or session.last_result.sql is None:
        console.print("[dim]No SQL to display.[/dim]")
        return False

    from mintq.cli.display import render_sql

    render_sql(console, session.last_result.sql)
    return False


async def _cmd_result_table(args: list[str], session: ChatSession, console: Console) -> bool:
    if session.last_result is None or session.last_result.df is None or session.last_result.df.empty:
        console.print("[dim]No table to display.[/dim]")
        return False

    from mintq.cli.display import render_table

    render_table(console, session.last_result.df)
    return False


_COMMAND_HELP: dict[str, tuple[object, str]] = {
    "/help": (_cmd_help, "Show this help message"),
    "/exit": (_cmd_exit, "Exit the chat"),
    "/clear": (_cmd_clear, "Clear the screen"),
    "/connect": (_cmd_connect, "Connect to a database: /connect <url> [alias]"),
    "/disconnect": (_cmd_disconnect, "Disconnect: /disconnect [alias]"),
    "/databases": (_cmd_databases, "List connected databases"),
    "/db": (_cmd_databases, "Alias for /databases"),
    "/use": (_cmd_use, "Switch active database: /use <alias>"),
    "/schema": (_cmd_schema, "Show schema: /schema [table] [column]"),
    "/mode": (_cmd_mode, "Toggle output mode: /mode <response|chart|data|sql|all>"),
    "/model": (_cmd_model, "Switch LLM: /model <identifier>"),
    "/agent": (_cmd_agent, "Switch agent: /agent <name>"),
    "/view": (_cmd_view, "View last result (Tab/Shift+Tab to cycle views)"),
    "/sql": (_cmd_sql, "Show SQL of last result"),
    "/data": (_cmd_result_table, "Show data table of last result"),
}

COMMANDS: dict[str, object] = {cmd: handler for cmd, (handler, _) in _COMMAND_HELP.items()}
