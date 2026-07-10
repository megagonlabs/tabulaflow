"""Slash-command handlers for the CLI chat."""

from __future__ import annotations

import os
import re
import shlex
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

from rich.console import RenderableType
from rich.text import Text

from tabulaflow.app.theme import ERROR
from tabulaflow.app.session import WORKSPACE_ALIAS, SessionState
from tabulaflow.core.db_connector import DB_FILE_SCHEMES, connect_url, connector_info, normalize_url, url_needs_password

if TYPE_CHECKING:
    from tabulaflow.core.db_connector.base import NL2QDBConnector

COMMAND_PREFIX = "/"

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
# Helpers
# ---------------------------------------------------------------------------


def _announce_connect(session: SessionState, alias: str, connector: NL2QDBConnector) -> str:
    """Tell the agent the user just connected ``alias`` (so it gains temporal
    awareness of the new source) and return the connector's display summary."""
    info = connector_info(connector)
    session.chat_agent.note_event(f"the user just connected a new data source `{alias}` ({info}).")
    return info


def _is_data_file(path: str) -> bool:
    from tabulaflow.datasources.files import DATA_FILE_EXTENSIONS

    return os.path.splitext(path)[1].lower() in DATA_FILE_EXTENSIONS


def _is_db_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in DB_FILE_SCHEMES


def _sanitize_alias(raw: str) -> str:
    """Convert a raw string to a valid alias containing only [a-z0-9_]."""
    name = os.path.splitext(os.path.basename(raw))[0]
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_").lower()
    return name or "db"


def _alias_from_files(file_paths: list[str]) -> str:
    if len(file_paths) == 1:
        return _sanitize_alias(file_paths[0])
    return "local_files"


def _alias_from_url(url: str) -> str:
    if ":///" in url:
        path = url.split("///", 1)[-1]
        return _sanitize_alias(os.path.basename(path))
    parsed = urlparse(url)
    if parsed.path and parsed.path.strip("/"):
        segment = parsed.path.strip("/").rsplit("/", 1)[-1]
        return _sanitize_alias(segment)
    if parsed.hostname:
        return _sanitize_alias(parsed.hostname)
    return _sanitize_alias(url)


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
        return CommandResult(
            output=Text.from_markup(f"[{ERROR}]Unknown command:[/] {cmd}. Type /help for available commands.")
        )

    return await handler(args, session)  # type: ignore[operator, no-any-return]


async def _cmd_help(args: list[str], session: SessionState) -> CommandResult:
    lines = Text()
    for cmd, (_, description) in _COMMAND_HELP.items():
        lines.append(f"  {cmd}\n", style="bold")
        lines.append(f"    {description}\n", style="dim")
    return CommandResult(output=lines)


async def _cmd_exit(args: list[str], session: SessionState) -> CommandResult:
    # Disconnect happens in the TUI's exit path so all quit triggers
    # (slash command, idle Ctrl+C / Ctrl+D double-press, …) share one
    # cleanup site.  See ``TabulaflowApp._request_exit``.
    return CommandResult(should_quit=True)


async def _cmd_clear(args: list[str], session: SessionState) -> CommandResult:
    return CommandResult(should_clear=True)


async def _cmd_connect(args: list[str], session: SessionState) -> CommandResult:
    if not args:
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Usage:[/] /connect <url_or_path> \\[alias]\n"
                "[dim]  /connect ./data/schools.sqlite\n"
                "  /connect ./sales.csv\n"
                "  /connect ./sales.csv ./inventory.csv mydb\n"
                "  /connect ./report.xlsx\n"
                "  /connect sqlite+aiosqlite:///path/to/db.sqlite\n"
                "  /connect bigquery://bigquery-public-data/noaa_gsod\n"
                "  /connect snowflake://user@account/db\n"
                "  /connect duckdb:///path/to/db.duckdb\n"
                "  /connect neo4j://neo4j:password@localhost:7687\n"
                "  /connect bolt://localhost:7687?database=neo4j myalias\n"
                "  /connect https://huggingface.co/datasets/stanfordnlp/imdb\n"
                "  /connect https://huggingface.co/datasets/nyu-mll/glue/viewer/mrpc/train[/dim]"
            )
        )

    # --- Data file connections ---
    file_args = [a for a in args if _is_data_file(a)]
    if file_args:
        non_file_args = [a for a in args if not _is_data_file(a)]
        db_file_args = [a for a in non_file_args if _is_db_file(a)]
        if db_file_args:
            return CommandResult(
                output=Text.from_markup(
                    f"[{ERROR}]Cannot mix database files and data files.[/] "
                    "Connect them separately:\n"
                    f"[dim]  /connect {db_file_args[0]}\n"
                    f"  /connect {' '.join(os.path.basename(f) for f in file_args)}[/dim]"
                )
            )

        # Source-identity dedup: reject if the same set of files is
        # already loaded under another alias (regardless of what alias
        # was requested this time).
        source_key = ("files", frozenset(os.path.abspath(os.path.expanduser(f)) for f in file_args))
        existing = session.find_alias_by_source(source_key)
        if existing is not None:
            return CommandResult(
                output=Text.from_markup(
                    f"[{ERROR}]Already loaded as[/] {existing}. "
                    f"Use that alias, or [dim]/disconnect {existing}[/dim] first to reload."
                )
            )

        alias_args = [a for a in non_file_args if not _is_db_file(a)]
        if alias_args:
            alias = _sanitize_alias(alias_args[0])
            if session.registry.has(alias):
                return CommandResult(
                    output=Text.from_markup(
                        f"[{ERROR}]Alias already in use:[/] {alias}. "
                        "Disconnect first or provide a different alias: /connect <files...> <alias>"
                    )
                )
        else:
            # Auto-derived alias — suffix on collision so different files
            # mapping to the same default name don't fight (e.g. /A/data.csv
            # and /B/data.csv both default to "data").
            base_alias = _alias_from_files(file_args)
            alias = base_alias
            suffix = 2
            while session.registry.has(alias):
                alias = f"{base_alias}_{suffix}"
                suffix += 1

        from tabulaflow.datasources.files import load_files

        global_id = f"cli+{alias}"
        file_label = ", ".join(os.path.basename(f) for f in file_args)
        try:
            connector = await load_files(
                global_id=global_id,
                file_paths=file_args,
                db_name=alias,
                data_dir=str(session.data_dir),
                read_only=True,
                enable_schema_caching=False,
                enable_query_caching=False,
            )
        except Exception as e:
            return CommandResult(output=Text.from_markup(f"[{ERROR}]Failed to load files:[/] {e}"))

        await session.register_db(alias, connector, source_key)
        info = _announce_connect(session, alias, connector)
        return CommandResult(output=Text(f"✓ Loaded {file_label} as {alias} ({info})", style="dim"))

    # --- HuggingFace dataset connections ---
    from tabulaflow.datasources import is_hf_dataset_url

    if is_hf_dataset_url(args[0]):
        return await _connect_hf_dataset(args, session)

    if "huggingface.co" in args[0]:
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Unsupported HuggingFace URL format.[/]\n"
                "[dim]Expected: https://huggingface.co/datasets/\\<owner>/\\<dataset>\\[/viewer/\\<subset>\\[/\\<split>\\]\\][/dim]"
            )
        )

    # --- URL / database-file connections ---
    raw = args[0]
    url = normalize_url(raw)
    alias = _sanitize_alias(args[1]) if len(args) > 1 else _alias_from_url(url)

    url_source_key = ("url", url)
    existing = session.find_alias_by_source(url_source_key)
    if existing is not None:
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Already connected as[/] {existing}. "
                f"Use that alias, or [dim]/disconnect {existing}[/dim] first to reconnect."
            )
        )

    if session.registry.has(alias):
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Alias already in use:[/] {alias}. "
                "Disconnect first or provide a different alias: /connect <url> <alias>"
            )
        )

    # Check if password prompt is needed
    if url_needs_password(url):
        return CommandResult(password_prompt=f"connect:{url}:{alias}")

    return await _execute_connect(url, alias, session)


async def _connect_hf_dataset(args: list[str], session: SessionState) -> CommandResult:
    """Handle /connect for HuggingFace dataset URLs."""
    from tabulaflow.datasources import load_hf_dataset, parse_hf_dataset_url

    url = args[0]
    try:
        dataset_id, _, _ = parse_hf_dataset_url(url)
    except ValueError as e:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]{e}[/]"))

    source_key = ("hf", url)
    existing = session.find_alias_by_source(source_key)
    if existing is not None:
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Already loaded as[/] {existing}. "
                f"Use that alias, or [dim]/disconnect {existing}[/dim] first to reload."
            )
        )

    default_alias = _sanitize_alias(dataset_id.split("/")[-1])
    alias = _sanitize_alias(args[1]) if len(args) > 1 else default_alias

    if session.registry.has(alias):
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Alias already in use:[/] {alias}. "
                "Disconnect first or provide a different alias: /connect <url> <alias>"
            )
        )

    try:
        from tabulaflow.modulehub.text_summarizer import TextSummarizer

        connector = await load_hf_dataset(
            url,
            db_name=alias,
            read_only=True,
            summarize=TextSummarizer().summarize,
        )
    except Exception as e:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]Failed to load HF dataset:[/] {e}"))

    await session.register_db(alias, connector, source_key)
    info = _announce_connect(session, alias, connector)
    return CommandResult(output=Text(f"✓ Loaded {dataset_id} as {alias} ({info})", style="dim"))


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
    try:
        connector = await connect_url(url, db_name=alias, read_only=True)
    except Exception as e:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]Connection failed:[/] {e}"))

    await session.register_db(alias, connector, ("url", url))
    info = _announce_connect(session, alias, connector)
    return CommandResult(output=Text(f"✓ Connected to {alias} ({info})", style="dim"))


async def _cmd_disconnect(args: list[str], session: SessionState) -> CommandResult:
    aliases = session.registry.list_aliases()
    user_aliases = [alias for alias in aliases if alias != WORKSPACE_ALIAS]
    if not args:
        if len(user_aliases) == 1:
            alias = user_aliases[0]
        else:
            return CommandResult(output=Text.from_markup(f"[{ERROR}]Usage:[/] /disconnect <alias>"))
    else:
        alias = args[0]

    if alias == WORKSPACE_ALIAS:
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Cannot disconnect[/] [bold]{WORKSPACE_ALIAS}[/bold] — the workspace is built-in."
            )
        )

    if await session.registry.unregister_async(alias):
        session.unregister_alias_sources(alias)
        session.chat_agent.note_event(f"the user disconnected the data source `{alias}`; it is no longer available.")
        return CommandResult(output=Text(f"✓ Disconnected from {alias}", style="dim"))
    else:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]No connection named:[/] {alias}"))


_COMMAND_HELP: dict[str, tuple[object, str]] = {
    "/help": (_cmd_help, "Show this help message"),
    "/exit": (_cmd_exit, "Exit the chat"),
    "/clear": (_cmd_clear, "Clear the screen"),
    "/connect": (_cmd_connect, "Connect to a database: /connect <url> \\[alias]"),
    "/disconnect": (_cmd_disconnect, "Disconnect: /disconnect \\[alias]"),
}

COMMANDS: dict[str, object] = {cmd: handler for cmd, (handler, _) in _COMMAND_HELP.items()}
