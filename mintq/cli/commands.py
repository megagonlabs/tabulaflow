"""Slash-command handlers for the CLI chat."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from mintq.cli.chat import ChatSession

COMMAND_PREFIX = "/"


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
    table = Table(title="Commands", show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("Command", style="bold")
    table.add_column("Description")

    for cmd, (_, description) in _COMMAND_HELP.items():
        table.add_row(cmd, description)

    console.print(table)
    return False


async def _cmd_quit(args: list[str], session: ChatSession, console: Console) -> bool:
    await session.connections.disconnect_all()
    console.print("[dim]Goodbye![/dim]")
    return True


async def _cmd_clear(args: list[str], session: ChatSession, console: Console) -> bool:
    console.clear()
    return False


async def _cmd_connect(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print("[red]Usage:[/red] /connect <url> [alias]")
        return False

    url = args[0]
    alias = args[1] if len(args) > 1 else _alias_from_url(url)

    from mintq.db_connector import SQLConnector

    with console.status(f"[cyan]Connecting to {alias}...[/cyan]"):
        try:
            connector = await SQLConnector.from_url_async(
                global_id=alias,
                db_name=alias,
                engine_type="sqlalchemy",
                url=url,
                read_only=True,
            )
        except Exception as e:
            console.print(f"[red]Connection failed:[/red] {e}")
            return False

    n_tables = len(connector.schema.tables) if connector.schema else 0
    session.connections.add(alias, connector)
    console.print(f"[green]✓[/green] Connected to [bold]{alias}[/bold] ({n_tables} tables)")
    return False


async def _cmd_disconnect(args: list[str], session: ChatSession, console: Console) -> bool:
    alias = args[0] if args else session.connections.active_alias
    if alias is None:
        console.print("[red]No active connection.[/red]")
        return False
    if await session.connections.remove(alias):
        console.print(f"[green]✓[/green] Disconnected from [bold]{alias}[/bold]")
    else:
        console.print(f"[red]No connection named:[/red] {alias}")
    return False


async def _cmd_databases(args: list[str], session: ChatSession, console: Console) -> bool:
    connections = session.connections.list_all()
    if not connections:
        console.print("[dim]No databases connected. Use /connect <url> to add one.[/dim]")
        return False

    table = Table(show_header=True, header_style="bold magenta")
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
        console.print(f"[green]✓[/green] Switched to [bold]{args[0]}[/bold]")
    else:
        console.print(f"[red]No connection named:[/red] {args[0]}")
    return False


async def _cmd_schema(args: list[str], session: ChatSession, console: Console) -> bool:
    conn = session.connections.active_connector
    if conn is None:
        console.print("[red]No active connection.[/red] Use /connect first.")
        return False

    schema = conn.schema
    if schema is None:
        console.print("[dim]Schema not available.[/dim]")
        return False

    if args:
        table_name = args[0]
        tbl = next((t for t in schema.tables if t.name == table_name), None)
        if tbl is None:
            console.print(f"[red]Table not found:[/red] {table_name}")
            return False
        _print_table_detail(console, tbl)
    else:
        _print_schema_overview(console, schema, session.connections.active_alias or "")

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
    console.print(f"[green]✓[/green] Model set to [bold]{session.model}[/bold]")
    return False


async def _cmd_agent(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print(f"[dim]Current agent:[/dim] {session.agent_name}")
        return False
    session.agent_name = args[0]
    console.print(f"[green]✓[/green] Agent set to [bold]{session.agent_name}[/bold]")
    return False


def _alias_from_url(url: str) -> str:
    """Derive a short alias from a database URL."""
    if "///" in url:
        path = url.split("///")[-1]
        return path.rsplit("/", 1)[-1].split(".")[0]
    if "//" in url:
        parts = url.split("/")
        return parts[-1] if parts[-1] else parts[-2]
    return url


def _print_schema_overview(console: Console, schema: object, alias: str) -> None:
    from mintq.schema import SQLSchema

    assert isinstance(schema, SQLSchema)
    table = Table(title=f"[bold]{alias}[/bold]", show_header=True, header_style="bold magenta")
    table.add_column("Table")
    table.add_column("Columns", justify="right")

    for tbl in schema.tables:
        table.add_row(tbl.name, str(len(tbl.columns)))

    console.print(table)


def _print_table_detail(console: Console, tbl: object) -> None:
    from mintq.schema import SQLTableSchema

    assert isinstance(tbl, SQLTableSchema)
    table = Table(title=f"[bold]{tbl.name}[/bold]", show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("Column")
    table.add_column("Type")

    for col in tbl.columns:
        table.add_row(col.name, col.type or "")

    console.print(table)


_COMMAND_HELP: dict[str, tuple[object, str]] = {
    "/help": (_cmd_help, "Show this help message"),
    "/quit": (_cmd_quit, "Exit the chat"),
    "/clear": (_cmd_clear, "Clear the screen"),
    "/connect": (_cmd_connect, "Connect to a database: /connect <url> [alias]"),
    "/disconnect": (_cmd_disconnect, "Disconnect: /disconnect [alias]"),
    "/databases": (_cmd_databases, "List connected databases"),
    "/db": (_cmd_databases, "Alias for /databases"),
    "/use": (_cmd_use, "Switch active database: /use <alias>"),
    "/schema": (_cmd_schema, "Show schema: /schema [table]"),
    "/mode": (_cmd_mode, "Toggle output mode: /mode <nl|sql|table|chart|all>"),
    "/model": (_cmd_model, "Switch LLM: /model <identifier>"),
    "/agent": (_cmd_agent, "Switch agent: /agent <name>"),
}

COMMANDS: dict[str, object] = {cmd: handler for cmd, (handler, _) in _COMMAND_HELP.items()}
