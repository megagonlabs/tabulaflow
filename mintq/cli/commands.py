"""Slash-command handlers for the CLI chat."""

from __future__ import annotations

import os
import shlex
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rich.console import Console
from rich.table import Table

from mintq.cli.theme import ACCENT, ACCENT_BOLD
if TYPE_CHECKING:
    from mintq.cli.chat import ChatSession
    from mintq.schema import SQLSchema

COMMAND_PREFIX = "/"

_FILE_EXTENSIONS: dict[str, str] = {
    ".sqlite": "sqlite+aiosqlite",
    ".sqlite3": "sqlite+aiosqlite",
    ".db": "sqlite+aiosqlite",
    ".duckdb": "duckdb",
}

_DATA_FILE_EXTENSIONS = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson"})


def _is_data_file(path: str) -> bool:
    """Check if a path looks like a supported data file."""
    return os.path.splitext(path)[1].lower() in _DATA_FILE_EXTENSIONS


def _alias_from_files(file_paths: list[str]) -> str:
    """Derive a short alias from data file paths."""
    return os.path.splitext(os.path.basename(file_paths[0]))[0]


def _engine_kwargs_for_url(url: str) -> dict[str, Any]:
    """Build connector engine kwargs based on URL scheme."""
    scheme = url.split("://", 1)[0].split("+", 1)[0].lower()
    if scheme != "bigquery":
        return {}

    google_cloud_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_BILLING_PROJECT")
    if not google_cloud_project:
        raise ValueError("BigQuery billing project required: set GOOGLE_CLOUD_PROJECT (or GCP_BILLING_PROJECT).")

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

    return await handler(args, session, console)  # type: ignore[operator, no-any-return]


async def _cmd_help(args: list[str], session: ChatSession, console: Console) -> bool:
    table = Table(title="Commands", show_header=True, header_style=ACCENT_BOLD, show_lines=False)
    table.add_column("Command", style="bold")
    table.add_column("Description")

    for cmd, (_, description) in _COMMAND_HELP.items():
        table.add_row(cmd, description)

    console.print(table)
    return False


async def _cmd_exit(args: list[str], session: ChatSession, console: Console) -> bool:
    await session.registry.disconnect_all_async()
    return True


async def _cmd_clear(args: list[str], session: ChatSession, console: Console) -> bool:
    console.clear()
    return False


async def _cmd_connect(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print(
            "[red]Usage:[/red] /connect <url_or_path> [alias]\n"
            "[dim]  /connect ./data/schools.sqlite\n"
            "  /connect ./sales.csv\n"
            "  /connect ./sales.csv ./inventory.csv mydb\n"
            "  /connect ./report.xlsx\n"
            "  /connect sqlite+aiosqlite:///path/to/db.sqlite\n"
            "  /connect bigquery://bigquery-public-data/noaa_gsod\n"
            "  /connect snowflake://user@account/db\n"
            "  /connect duckdb:///path/to/db.duckdb\n"
            "  /connect neo4j://neo4j:password@localhost:7687\n"
            "  /connect bolt://localhost:7687?database=neo4j myalias[/dim]"
        )
        return False

    # --- Data file connections (CSV, Excel, Parquet, etc.) ---
    file_args = [a for a in args if _is_data_file(a)]
    if file_args:
        non_file_args = [a for a in args if not _is_data_file(a)]
        alias = non_file_args[0] if non_file_args else _alias_from_files(file_args)

        if session.registry.has(alias):
            console.print(
                f"[red]Alias already in use:[/red] {alias}. "
                "Disconnect first or provide a different alias: /connect <files...> <alias>"
            )
            return False

        from mintq.db_connector.sql_conn import SQLConnector

        global_id = f"cli+{alias}"
        file_label = ", ".join(os.path.basename(f) for f in file_args)
        with console.status(f"[dim]Loading {file_label}...[/dim]", spinner_style=ACCENT):
            try:
                connector = await SQLConnector.from_files_async(
                    global_id=global_id,
                    file_paths=file_args,
                    db_name=alias,
                    read_only=True,
                    enable_schema_caching=False,
                    enable_query_caching=False,
                )
            except Exception as e:
                console.print(f"[red]Failed to load files:[/red] {e}")
                return False

        n_tables = len(connector.schema.tables)
        session.registry.register(alias, connector)
        console.print(
            f"[{ACCENT}]✓[/{ACCENT}] Loaded [bold]{file_label}[/bold] as "
            f"[bold]{alias}[/bold] (duckdb, {n_tables} table{'s' if n_tables != 1 else ''})"
        )
        return False

    # --- URL / database-file connections ---
    raw = args[0]
    url = _normalize_url(raw)
    alias = args[1] if len(args) > 1 else _alias_from_url(url)

    if session.registry.has(alias):
        console.print(
            f"[red]Alias already in use:[/red] {alias}. "
            "Disconnect first or provide a different alias: /connect <url> <alias>"
        )
        return False

    url = await _prompt_password_if_needed(url, console)

    global_id = f"cli+{alias}"
    if _is_neo4j_bolt_url(url):
        from mintq.db_connector.neo4j_conn import Neo4jConnector

        driver_url, neo4j_database = _neo4j_driver_url_and_database(url)
        with console.status(f"[dim]Connecting to {alias}...[/dim]", spinner_style=ACCENT):
            try:
                neo_connector = await Neo4jConnector.from_url_async(
                    global_id=global_id,
                    url=driver_url,
                    database=neo4j_database,
                    db_name=alias,
                    read_only=True,
                    auth=("neo4j", "cypherbench"),
                    enable_schema_caching=True,
                )
            except Exception as e:
                console.print(f"[red]Connection failed:[/red] {e}")
                return False

        n_labels = len(neo_connector.schema.nodes)
        n_patterns = len(neo_connector.schema.relationships)
        session.registry.register(alias, neo_connector)
        console.print(
            f"[{ACCENT}]✓[/{ACCENT}] Connected to [bold]{alias}[/bold] "
            f"(cypher, {n_labels} label{'s' if n_labels != 1 else ''}, "
            f"{n_patterns} rel pattern{'s' if n_patterns != 1 else ''})"
        )
        return False

    try:
        engine_kwargs = _engine_kwargs_for_url(url)
    except ValueError as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        return False

    from mintq.db_connector.sql_conn import SQLConnector

    with console.status(f"[dim]Connecting to {alias}...[/dim]", spinner_style=ACCENT):
        try:
            connector = await SQLConnector.from_url_async(
                global_id=global_id,
                url=url,
                db_name=alias,
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
    session.registry.register(alias, connector)
    console.print(f"[{ACCENT}]✓[/{ACCENT}] Connected to [bold]{alias}[/bold] ({dialect}, {n_tables} tables)")
    return False


async def _cmd_disconnect(args: list[str], session: ChatSession, console: Console) -> bool:
    aliases = session.registry.list_aliases()
    if not args:
        if len(aliases) == 1:
            alias = aliases[0]
        else:
            console.print("[red]Usage:[/red] /disconnect <alias>")
            return False
    else:
        alias = args[0]

    if await session.registry.unregister_async(alias):
        console.print(f"[{ACCENT}]✓[/{ACCENT}] Disconnected from [bold]{alias}[/bold]")
    else:
        console.print(f"[red]No connection named:[/red] {alias}")
    return False


async def _cmd_databases(args: list[str], session: ChatSession, console: Console) -> bool:
    aliases = session.registry.list_aliases()
    if not aliases:
        console.print("[dim]No databases connected. Use /connect <url> to add one.[/dim]")
        return False

    from mintq.db_connector import Neo4jConnector

    table = Table(show_header=True, header_style=ACCENT_BOLD)
    table.add_column("Alias", style="bold")
    table.add_column("Schema")

    for alias in aliases:
        conn = session.registry.get(alias)
        if isinstance(conn, Neo4jConnector) and conn.schema:
            n_lab = len(conn.schema.nodes)
            n_rel = len(conn.schema.relationships)
            summary = f"{n_lab} labels, {n_rel} rel patterns"
        elif conn.schema and hasattr(conn.schema, "tables"):
            summary = f"{len(conn.schema.tables)} tables"
        else:
            summary = "?"
        table.add_row(alias, summary)

    console.print(table)
    return False


def _resolve_alias(args: list[str], session: ChatSession) -> tuple[str | None, list[str]]:
    """Resolve the database alias from command args.

    If the first arg matches a registered alias, consume it. If there is
    exactly one connected database, use it implicitly. Returns
    ``(alias, remaining_args)`` or ``(None, args)`` on ambiguity.
    """
    if args and session.registry.has(args[0]):
        return args[0], args[1:]
    aliases = session.registry.list_aliases()
    if len(aliases) == 1:
        return aliases[0], args
    return None, args


async def _cmd_schema(args: list[str], session: ChatSession, console: Console) -> bool:
    from mintq.cli.display import (
        render_schema_overview,
        render_table_detail,
        render_column_detail,
        resolve_table,
        resolve_column,
        _is_multi_schema,
        _display_name,
        render_property_graph_overview,
        render_graph_node_detail,
        render_graph_reltype_detail,
        resolve_graph_node_label,
        resolve_graph_rel_patterns,
    )
    from mintq.db_connector import Neo4jConnector

    aliases = session.registry.list_aliases()
    if not aliases:
        console.print("[red]No database connected.[/red] Use /connect first.")
        return False

    alias, rest = _resolve_alias(args, session)
    if alias is None:
        if not args:
            console.print("[dim]Multiple databases connected. Specify alias: /schema <alias> [table] [column][/dim]")
            console.print(f"[dim]Available: {', '.join(aliases)}[/dim]")
        else:
            console.print(f"[red]Unknown alias or table:[/red] {args[0]}. Available databases: {', '.join(aliases)}")
        return False

    conn = session.registry.get(alias)
    schema = conn.schema
    if schema is None:
        console.print("[dim]Schema not available.[/dim]")
        return False

    if isinstance(conn, Neo4jConnector):
        graph_schema = conn.schema
        if not rest:
            render_property_graph_overview(console, graph_schema, alias)
            return False
        node = resolve_graph_node_label(graph_schema, rest[0])
        if node is not None:
            render_graph_node_detail(console, node)
            return False
        rel_patterns = resolve_graph_rel_patterns(graph_schema, rest[0])
        if rel_patterns:
            render_graph_reltype_detail(console, rest[0], rel_patterns)
            return False
        console.print(f"[red]Unknown label or relationship type:[/red] {rest[0]}")
        return False

    sql_schema = cast("SQLSchema", schema)
    multi = _is_multi_schema(sql_schema)

    if not rest:
        render_schema_overview(console, sql_schema, alias)
        return False

    result = resolve_table(sql_schema, rest[0])
    if result is None:
        console.print(f"[red]Table not found:[/red] {rest[0]}")
        return False
    if isinstance(result, list):
        console.print(f"[red]Ambiguous table name:[/red] {rest[0]}. Matches:")
        for t in result:
            console.print(f"  [dim]{_display_name(t, multi_schema=True)}[/dim]")
        console.print("[dim]Use the qualified name: /schema [alias] <schema>.<table>[/dim]")
        return False

    tbl = result

    if len(rest) < 2:
        render_table_detail(console, tbl, multi_schema=multi)
        return False

    col = resolve_column(tbl, rest[1])
    if col is None:
        console.print(f"[red]Column not found:[/red] {rest[1]} in {_display_name(tbl, multi)}")
        return False

    render_column_detail(console, tbl, col)
    return False


async def _cmd_model(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print(f"[dim]Current model:[/dim] {session.model}")
        return False
    session.set_model(args[0])
    console.print(f"[{ACCENT}]✓[/{ACCENT}] Model set to [bold]{session.model}[/bold]")
    return False


async def _cmd_agent(args: list[str], session: ChatSession, console: Console) -> bool:
    if not args:
        console.print(f"[dim]Current agent:[/dim] {session.agent_name}")
        return False
    session.agent_name = args[0]
    console.print(f"[{ACCENT}]✓[/{ACCENT}] Agent set to [bold]{session.agent_name}[/bold]")
    return False


_ASYNC_DRIVER_UPGRADES: dict[str, str] = {
    "sqlite": "sqlite+aiosqlite",
    "postgresql": "postgresql+asyncpg",
    "postgres": "postgresql+asyncpg",
    "mysql": "mysql+asyncmy",
}


def _is_neo4j_bolt_url(url: str) -> bool:
    """True if *url* uses a Neo4j Python driver scheme (Bolt / routing)."""
    if "://" not in url:
        return False
    scheme = url.split("://", 1)[0].lower()
    return scheme == "neo4j" or scheme.startswith("neo4j+") or scheme == "bolt" or scheme.startswith("bolt+")


def _neo4j_driver_url_and_database(url: str) -> tuple[str, str | None]:
    """Strip ``database`` / ``db`` query params for the driver URI; return Neo4j database name."""
    parsed = urlparse(url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    database: str | None = None
    kept: list[tuple[str, str]] = []
    for k, v in pairs:
        if k.lower() in ("database", "db"):
            if database is None and v:
                database = v
            continue
        kept.append((k, v))
    new_query = urlencode(kept) if kept else ""
    return urlunparse(parsed._replace(query=new_query)), database


def _normalize_url(raw: str) -> str:
    """Expand a bare file path into a SQLAlchemy URL, or return as-is."""
    for ext, scheme in _FILE_EXTENSIONS.items():
        if raw.endswith(ext):
            abspath = os.path.abspath(raw)
            return f"{scheme}:///{abspath}"

    if "://" in raw:
        scheme, rest = raw.split("://", 1)
        if "+" not in scheme and scheme in _ASYNC_DRIVER_UPGRADES:
            return f"{_ASYNC_DRIVER_UPGRADES[scheme]}://{rest}"

    return raw


async def _prompt_password_if_needed(url: str, console: Console) -> str:
    """If URL has a username but no password, prompt interactively."""
    parsed = urlparse(url)
    if parsed.username and not parsed.password and parsed.hostname:
        from prompt_toolkit import PromptSession as _PromptSession

        console.print(f"[dim]Authenticating as[/dim] [bold]{parsed.username}[/bold]")
        _ps: _PromptSession[str] = _PromptSession()
        password = await _ps.prompt_async(
            "  Password: ",
            is_password=True,
        )
        replaced = parsed._replace(
            netloc=f"{parsed.username}:{password}@{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")
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
    if session.last_result is None or session.last_result.query is None:
        console.print("[dim]No SQL to display.[/dim]")
        return False

    from mintq.cli.display import render_sql

    render_sql(console, session.last_result.query, lexer=session.last_result.query_lexer)
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
    "/schema": (_cmd_schema, "Show schema: /schema [alias] [table] [column]"),
    "/model": (_cmd_model, "Switch LLM: /model <identifier>"),
    "/agent": (_cmd_agent, "Switch agent: /agent <name>"),
    "/view": (_cmd_view, "View last result (Tab/Shift+Tab to cycle views)"),
    "/sql": (_cmd_sql, "Show SQL of last result"),
    "/data": (_cmd_result_table, "Show data table of last result"),
}

COMMANDS: dict[str, object] = {cmd: handler for cmd, (handler, _) in _COMMAND_HELP.items()}
