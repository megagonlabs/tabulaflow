"""Slash-command handlers for the CLI chat."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from mintq.cli.theme import ACCENT, ACCENT_BOLD

if TYPE_CHECKING:
    from mintq.schema import SQLSchema

COMMAND_PREFIX = "/"

_FILE_EXTENSIONS: dict[str, str] = {
    ".sqlite": "sqlite+aiosqlite",
    ".sqlite3": "sqlite+aiosqlite",
    ".db": "sqlite+aiosqlite",
    ".duckdb": "duckdb",
}

_DATA_FILE_EXTENSIONS = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson"})


# ---------------------------------------------------------------------------
# Command result
# ---------------------------------------------------------------------------


class CommandResult:
    """Result of a slash command execution."""

    def __init__(
        self,
        *,
        output: RenderableType | None = None,
        should_quit: bool = False,
        should_clear: bool = False,
        password_prompt: str | None = None,
    ) -> None:
        self.output = output
        self.should_quit = should_quit
        self.should_clear = should_clear
        self.password_prompt = password_prompt


# ---------------------------------------------------------------------------
# Session interface (avoids circular import with tui.py)
# ---------------------------------------------------------------------------


class SessionState:
    """Holds state for a single interactive session."""

    def __init__(self, model: str, agent: str, session_id: str, trajectories_dir: Path) -> None:
        from mintq.cli.agent import ChatAgent
        from mintq.db_connector.db_registry import DBRegistry

        self.agent_name = agent
        self.session_id = session_id
        self.registry: DBRegistry = DBRegistry()
        self.chat_agent: ChatAgent = ChatAgent(
            registry=self.registry,
            model=model,
            session_id=session_id,
            trajectory_log_dir=trajectories_dir,
        )
        self.last_result: object | None = None

    @property
    def model(self) -> str:
        return self.chat_agent.model

    def set_model(self, model: str) -> None:
        self.chat_agent.set_model(model)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_data_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in _DATA_FILE_EXTENSIONS


def _alias_from_files(file_paths: list[str]) -> str:
    return os.path.splitext(os.path.basename(file_paths[0]))[0]


def _engine_kwargs_for_url(url: str) -> dict[str, Any]:
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


_ASYNC_DRIVER_UPGRADES: dict[str, str] = {
    "sqlite": "sqlite+aiosqlite",
    "postgresql": "postgresql+asyncpg",
    "postgres": "postgresql+asyncpg",
    "mysql": "mysql+asyncmy",
}


def _is_neo4j_bolt_url(url: str) -> bool:
    if "://" not in url:
        return False
    scheme = url.split("://", 1)[0].lower()
    return scheme == "neo4j" or scheme.startswith("neo4j+") or scheme == "bolt" or scheme.startswith("bolt+")


def _neo4j_driver_url_and_database(url: str) -> tuple[str, str | None]:
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
    for ext, scheme in _FILE_EXTENSIONS.items():
        if raw.endswith(ext):
            abspath = os.path.abspath(raw)
            return f"{scheme}:///{abspath}"

    if "://" in raw:
        scheme, rest = raw.split("://", 1)
        if "+" not in scheme and scheme in _ASYNC_DRIVER_UPGRADES:
            return f"{_ASYNC_DRIVER_UPGRADES[scheme]}://{rest}"

    return raw


def _alias_from_url(url: str) -> str:
    if ":///" in url:
        path = url.split("///", 1)[-1]
        return os.path.splitext(os.path.basename(path))[0]
    parsed = urlparse(url)
    if parsed.path and parsed.path.strip("/"):
        return parsed.path.strip("/").rsplit("/", 1)[-1]
    if parsed.hostname:
        return parsed.hostname
    return url


def _resolve_alias(args: list[str], session: SessionState) -> tuple[str | None, list[str]]:
    if args and session.registry.has(args[0]):
        return args[0], args[1:]
    aliases = session.registry.list_aliases()
    if len(aliases) == 1:
        return aliases[0], args
    return None, args


def _url_needs_password(url: str) -> bool:
    """Check if URL has a username but no password."""
    parsed = urlparse(url)
    return bool(parsed.username and not parsed.password and parsed.hostname)


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------


async def handle_command(text: str, session: SessionState) -> CommandResult:
    """Dispatch a slash command. Returns a CommandResult."""
    parts = shlex.split(text)
    cmd = parts[0].lower()
    args = parts[1:]

    handler = COMMANDS.get(cmd)
    if handler is None:
        return CommandResult(output=Text(f"Unknown command: {cmd}. Type /help for available commands.", style="red"))

    return await handler(args, session)  # type: ignore[operator, no-any-return]


async def _cmd_help(args: list[str], session: SessionState) -> CommandResult:
    table = Table(title="Commands", show_header=True, header_style=ACCENT_BOLD, show_lines=False)
    table.add_column("Command", style="bold")
    table.add_column("Description")

    for cmd, (_, description) in _COMMAND_HELP.items():
        table.add_row(cmd, description)

    return CommandResult(output=table)


async def _cmd_exit(args: list[str], session: SessionState) -> CommandResult:
    await session.registry.disconnect_all_async()
    return CommandResult(should_quit=True)


async def _cmd_clear(args: list[str], session: SessionState) -> CommandResult:
    return CommandResult(should_clear=True)


async def _cmd_connect(args: list[str], session: SessionState) -> CommandResult:
    if not args:
        return CommandResult(
            output=Text.from_markup(
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
        )

    # --- Data file connections ---
    file_args = [a for a in args if _is_data_file(a)]
    if file_args:
        non_file_args = [a for a in args if not _is_data_file(a)]
        alias = non_file_args[0] if non_file_args else _alias_from_files(file_args)

        if session.registry.has(alias):
            return CommandResult(
                output=Text.from_markup(
                    f"[red]Alias already in use:[/red] {alias}. "
                    "Disconnect first or provide a different alias: /connect <files...> <alias>"
                )
            )

        from mintq.db_connector.sql_conn import SQLConnector

        global_id = f"cli+{alias}"
        file_label = ", ".join(os.path.basename(f) for f in file_args)
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
            return CommandResult(output=Text.from_markup(f"[red]Failed to load files:[/red] {e}"))

        session.registry.register(alias, connector)
        info = session.chat_agent.database_info(connector)
        session.chat_agent.add_database([(alias, connector)])
        return CommandResult(
            output=Text.from_markup(
                f"[{ACCENT}]✓[/{ACCENT}] Loaded [bold]{file_label}[/bold] as [bold]{alias}[/bold] ({info})"
            )
        )

    # --- URL / database-file connections ---
    raw = args[0]
    url = _normalize_url(raw)
    alias = args[1] if len(args) > 1 else _alias_from_url(url)

    if session.registry.has(alias):
        return CommandResult(
            output=Text.from_markup(
                f"[red]Alias already in use:[/red] {alias}. "
                "Disconnect first or provide a different alias: /connect <url> <alias>"
            )
        )

    # Check if password prompt is needed
    if _url_needs_password(url):
        return CommandResult(password_prompt=f"connect:{url}:{alias}")

    return await _execute_connect(url, alias, session)


async def execute_connect_with_password(url: str, alias: str, password: str, session: SessionState) -> CommandResult:
    """Complete a connection that required a password prompt."""
    parsed = urlparse(url)
    replaced = parsed._replace(
        netloc=f"{parsed.username}:{password}@{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")
    )
    url = urlunparse(replaced)
    return await _execute_connect(url, alias, session)


async def _execute_connect(url: str, alias: str, session: SessionState) -> CommandResult:
    """Execute the actual database connection."""
    global_id = f"cli+{alias}"

    if _is_neo4j_bolt_url(url):
        from mintq.db_connector.neo4j_conn import Neo4jConnector

        driver_url, neo4j_database = _neo4j_driver_url_and_database(url)
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
            return CommandResult(output=Text.from_markup(f"[red]Connection failed:[/red] {e}"))

        session.registry.register(alias, neo_connector)
        info = session.chat_agent.database_info(neo_connector)
        session.chat_agent.add_database([(alias, neo_connector)])
        return CommandResult(
            output=Text.from_markup(f"[{ACCENT}]✓[/{ACCENT}] Connected to [bold]{alias}[/bold] ({info})")
        )

    try:
        engine_kwargs = _engine_kwargs_for_url(url)
    except ValueError as e:
        return CommandResult(output=Text.from_markup(f"[red]Connection failed:[/red] {e}"))

    from mintq.db_connector.sql_conn import SQLConnector

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
        return CommandResult(output=Text.from_markup(f"[red]Connection failed:[/red] {e}"))

    session.registry.register(alias, connector)
    info = session.chat_agent.database_info(connector)
    session.chat_agent.add_database([(alias, connector)])
    return CommandResult(output=Text.from_markup(f"[{ACCENT}]✓[/{ACCENT}] Connected to [bold]{alias}[/bold] ({info})"))


async def _cmd_disconnect(args: list[str], session: SessionState) -> CommandResult:
    aliases = session.registry.list_aliases()
    if not args:
        if len(aliases) == 1:
            alias = aliases[0]
        else:
            return CommandResult(output=Text.from_markup("[red]Usage:[/red] /disconnect <alias>"))
    else:
        alias = args[0]

    if await session.registry.unregister_async(alias):
        return CommandResult(output=Text.from_markup(f"[{ACCENT}]✓[/{ACCENT}] Disconnected from [bold]{alias}[/bold]"))
    else:
        return CommandResult(output=Text.from_markup(f"[red]No connection named:[/red] {alias}"))


async def _cmd_databases(args: list[str], session: SessionState) -> CommandResult:
    aliases = session.registry.list_aliases()
    if not aliases:
        return CommandResult(output=Text("No databases connected. Use /connect <url> to add one.", style="dim"))

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

    return CommandResult(output=table)


async def _cmd_schema(args: list[str], session: SessionState) -> CommandResult:
    from mintq.cli.display import (
        _display_name,
        _is_multi_schema,
        build_column_detail,
        build_graph_node_detail,
        build_graph_reltype_detail,
        build_property_graph_overview,
        build_schema_overview,
        build_table_detail,
        resolve_column,
        resolve_graph_node_label,
        resolve_graph_rel_patterns,
        resolve_table,
    )
    from mintq.db_connector import Neo4jConnector

    aliases = session.registry.list_aliases()
    if not aliases:
        return CommandResult(output=Text.from_markup("[red]No database connected.[/red] Use /connect first."))

    alias, rest = _resolve_alias(args, session)
    if alias is None:
        if not args:
            return CommandResult(
                output=Text.from_markup(
                    "[dim]Multiple databases connected. Specify alias: /schema <alias> [table] [column][/dim]\n"
                    f"[dim]Available: {', '.join(aliases)}[/dim]"
                )
            )
        else:
            return CommandResult(
                output=Text.from_markup(
                    f"[red]Unknown alias or table:[/red] {args[0]}. Available databases: {', '.join(aliases)}"
                )
            )

    conn = session.registry.get(alias)
    schema = conn.schema
    if schema is None:
        return CommandResult(output=Text("Schema not available.", style="dim"))

    if isinstance(conn, Neo4jConnector):
        graph_schema = conn.schema
        if not rest:
            return CommandResult(output=build_property_graph_overview(graph_schema, alias))
        node = resolve_graph_node_label(graph_schema, rest[0])
        if node is not None:
            return CommandResult(output=build_graph_node_detail(node))
        rel_patterns = resolve_graph_rel_patterns(graph_schema, rest[0])
        if rel_patterns:
            return CommandResult(output=build_graph_reltype_detail(rest[0], rel_patterns))
        return CommandResult(output=Text.from_markup(f"[red]Unknown label or relationship type:[/red] {rest[0]}"))

    sql_schema = cast("SQLSchema", schema)
    multi = _is_multi_schema(sql_schema)

    if not rest:
        return CommandResult(output=build_schema_overview(sql_schema, alias))

    result = resolve_table(sql_schema, rest[0])
    if result is None:
        return CommandResult(output=Text.from_markup(f"[red]Table not found:[/red] {rest[0]}"))
    if isinstance(result, list):
        lines = [f"[red]Ambiguous table name:[/red] {rest[0]}. Matches:"]
        for t in result:
            lines.append(f"  [dim]{_display_name(t, multi_schema=True)}[/dim]")
        lines.append("[dim]Use the qualified name: /schema [alias] <schema>.<table>[/dim]")
        return CommandResult(output=Text.from_markup("\n".join(lines)))

    tbl = result

    if len(rest) < 2:
        return CommandResult(output=build_table_detail(tbl, multi_schema=multi))

    col = resolve_column(tbl, rest[1])
    if col is None:
        return CommandResult(
            output=Text.from_markup(f"[red]Column not found:[/red] {rest[1]} in {_display_name(tbl, multi)}")
        )

    return CommandResult(output=build_column_detail(tbl, col))


async def _cmd_model(args: list[str], session: SessionState) -> CommandResult:
    if not args:
        return CommandResult(output=Text.from_markup(f"[dim]Current model:[/dim] {session.model}"))
    session.set_model(args[0])
    return CommandResult(output=Text.from_markup(f"[{ACCENT}]✓[/{ACCENT}] Model set to [bold]{session.model}[/bold]"))


async def _cmd_agent(args: list[str], session: SessionState) -> CommandResult:
    if not args:
        return CommandResult(output=Text.from_markup(f"[dim]Current agent:[/dim] {session.agent_name}"))
    session.agent_name = args[0]
    return CommandResult(
        output=Text.from_markup(f"[{ACCENT}]✓[/{ACCENT}] Agent set to [bold]{session.agent_name}[/bold]")
    )


async def _cmd_view(args: list[str], session: SessionState) -> CommandResult:
    if session.last_result is None:
        return CommandResult(output=Text("No result to display. Ask a question first.", style="dim"))
    # In the TUI, the result is already displayed in an AgentResultWidget.
    # This command is kept for compatibility but is a no-op in the TUI.
    return CommandResult(output=Text("Use arrow keys on a result widget to switch tabs.", style="dim"))


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
    "/view": (_cmd_view, "View last result (use arrow keys on result widget)"),
}

COMMANDS: dict[str, object] = {cmd: handler for cmd, (handler, _) in _COMMAND_HELP.items()}
