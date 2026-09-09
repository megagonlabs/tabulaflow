"""Slash-command handlers for the CLI chat."""

from __future__ import annotations

import os
import re
import shlex
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse

from rich.console import RenderableType
from rich.markup import escape
from rich.text import Text

from tabulaflow.app.tui.theme import ERROR
from tabulaflow.app.session import WORKSPACE_ALIAS, AppSession
from tabulaflow.data import connect_data_source
from tabulaflow.data.catalog import resolve_data_source_definition
from tabulaflow.data.connect import (
    is_database_file_path,
    normalize_connection_url,
    strip_url_credentials,
)
from tabulaflow.output.formatting import format_connector_summary

if TYPE_CHECKING:
    from tabulaflow.data.protocols import DataConnector

COMMAND_PREFIX = "/"


CommandAction = Literal["quit", "clear", "open_config"]


@dataclass(frozen=True)
class CommandResult:
    """Result of a slash command execution."""

    output: RenderableType | None = None
    action: CommandAction | None = None


@dataclass(frozen=True)
class ConnectCommand:
    """Parsed arguments for ``/connect``."""

    sources: tuple[str, ...]
    alias: str | None = None


CommandHandler = Callable[[list[str], AppSession], Awaitable[CommandResult]]


def _announce_connect(
    session: AppSession,
    alias: str,
    connector: DataConnector,
    guidance: str | None = None,
) -> str:
    """Tell the agent the user just connected ``alias`` (so it gains temporal
    awareness of the new source) and return the connector's display summary."""
    info = format_connector_summary(connector)
    message = f"the user just connected a new data source `{alias}` ({info})."
    if guidance:
        message += f"\n\n{guidance}\n\nUse get_data_source_document for complete source documentation."
    session.note_event(message)
    return info


def _is_data_file(path: str) -> bool:
    from tabulaflow.data.loaders.files import DATA_FILE_EXTENSIONS

    return os.path.splitext(path)[1].lower() in DATA_FILE_EXTENSIONS


def _is_db_file(path: str) -> bool:
    return is_database_file_path(path)


def _sanitize_alias(raw: str) -> str:
    """Convert a raw string to a valid alias containing only [a-z0-9_]."""
    name = os.path.splitext(os.path.basename(raw))[0]
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_").lower()
    return name or "db"


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


def _parse_connect_args(args: list[str]) -> ConnectCommand:
    sources: list[str] = []
    alias: str | None = None
    index = 0
    while index < len(args):
        argument = args[index]
        if argument in {"--alias", "-a"}:
            if alias is not None:
                raise ValueError("--alias may only be provided once")
            index += 1
            if index >= len(args):
                raise ValueError("--alias requires a value")
            alias = args[index]
        else:
            sources.append(argument)
        index += 1
    if not sources:
        raise ValueError("a source is required")
    if alias is not None and re.fullmatch(r"[A-Za-z0-9_]+", alias) is None:
        raise ValueError("alias may contain only letters, digits, and underscores")
    return ConnectCommand(sources=tuple(sources), alias=alias)


def _default_connect_alias(command: ConnectCommand, session: AppSession) -> str:
    if len(command.sources) > 1:
        return "local_files"
    source = command.sources[0]
    definition = resolve_data_source_definition(source, session.data_source_definitions)
    if definition is not None:
        return _sanitize_alias(definition.id)

    from tabulaflow.data.loaders import is_hf_dataset_url, parse_hf_dataset_url

    if is_hf_dataset_url(source):
        dataset_id, _, _ = parse_hf_dataset_url(source)
        return _sanitize_alias(dataset_id.rsplit("/", 1)[-1])
    if _is_data_file(source) or _is_db_file(source):
        return _sanitize_alias(source)
    return _alias_from_url(normalize_connection_url(source))


def _available_alias(base: str, session: AppSession) -> str:
    alias = base
    suffix = 2
    while session.registry.has(alias):
        alias = f"{base}_{suffix}"
        suffix += 1
    return alias


async def handle_command(text: str, session: AppSession) -> CommandResult:
    """Dispatch a slash command. Returns a CommandResult."""
    try:
        parts = shlex.split(text)
    except ValueError as e:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]Invalid command syntax:[/] {escape(str(e))}"))

    cmd = parts[0].lower()
    args = parts[1:]

    command = _COMMANDS.get(cmd)
    if command is None:
        return CommandResult(
            output=Text.from_markup(f"[{ERROR}]Unknown command:[/] {escape(cmd)}. Type /help for available commands.")
        )

    handler, _ = command
    return await handler(args, session)


async def _cmd_help(args: list[str], session: AppSession) -> CommandResult:
    lines = Text()
    for cmd, (_, description) in _COMMANDS.items():
        lines.append(f"  {cmd}\n", style="bold")
        lines.append(f"    {description}\n", style="dim")
    return CommandResult(output=lines)


async def _cmd_exit(args: list[str], session: AppSession) -> CommandResult:
    # Disconnect happens in the TUI's exit path so all quit triggers
    # (slash command, idle Ctrl+C / Ctrl+D double-press, …) share one
    # cleanup site.  See ``TabulaflowApp._request_exit``.
    return CommandResult(action="quit")


async def _cmd_clear(args: list[str], session: AppSession) -> CommandResult:
    session.reset_conversation()
    return CommandResult(action="clear")


async def _cmd_connect(args: list[str], session: AppSession) -> CommandResult:
    if not args:
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Usage:[/] /connect <source...> \\[--alias alias]\n"
                "[dim]  /connect wikidata\n"
                "  /connect ./data/schools.sqlite\n"
                "  /connect ./sales.csv\n"
                "  /connect ./sales.csv ./inventory.csv --alias mydb\n"
                "  /connect ./report.xlsx\n"
                "  /connect sqlite+aiosqlite:///path/to/db.sqlite\n"
                "  /connect bigquery://bigquery-public-data/noaa_gsod\n"
                "  /connect snowflake://user@account/db\n"
                "  /connect duckdb:///path/to/db.duckdb\n"
                "  /connect neo4j://neo4j:password@localhost:7687\n"
                "  /connect bolt://localhost:7687?database=neo4j --alias myalias\n"
                "  /connect sparql+https://query.wikidata.org/sparql --alias wikidata\n"
                "  /connect https://huggingface.co/datasets/stanfordnlp/imdb\n"
                "  /connect https://huggingface.co/datasets/nyu-mll/glue/viewer/mrpc/train[/dim]"
            )
        )
    try:
        command = _parse_connect_args(args)
    except ValueError as e:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]Invalid /connect syntax:[/] {escape(str(e))}"))

    alias = command.alias or _available_alias(_default_connect_alias(command, session), session)
    if command.alias is not None and session.registry.has(alias):
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Alias already in use:[/] {alias}. "
                "Disconnect first or provide a different alias with --alias."
            )
        )

    source: str | tuple[str, ...] = command.sources[0] if len(command.sources) == 1 else command.sources
    try:
        connector = await connect_data_source(
            source,
            display_name=alias,
            definitions=session.data_source_definitions,
            data_dir=session.data_dir,
            read_only=True,
            configs=session.connector_configs,
        )
    except Exception as e:
        safe_sources = [strip_url_credentials(item) if "://" in item else item for item in command.sources]
        source_label = ", ".join(repr(item) for item in safe_sources)
        return CommandResult(
            output=Text.from_markup(
                f"[{ERROR}]Failed to connect {escape(source_label)}:[/] {escape(f'{type(e).__name__}: {e}')}"
            )
        )

    session.registry.register(alias, connector)
    definition = (
        resolve_data_source_definition(command.sources[0], session.data_source_definitions)
        if len(command.sources) == 1
        else None
    )
    guidance = definition.description.strip() if definition is not None else None
    info = _announce_connect(session, alias, connector, guidance)
    return CommandResult(output=Text(f"✓ Connected to {alias} ({info})", style="dim"))


async def _cmd_disconnect(args: list[str], session: AppSession) -> CommandResult:
    if len(args) > 1:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]Usage:[/] /disconnect <alias>"))

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

    if await session.disconnect_source(alias):
        return CommandResult(output=Text(f"✓ Disconnected from {alias}", style="dim"))
    else:
        return CommandResult(output=Text.from_markup(f"[{ERROR}]No connection named:[/] {escape(alias)}"))


async def _cmd_config(args: list[str], session: AppSession) -> CommandResult:
    return CommandResult(action="open_config")


_COMMANDS: dict[str, tuple[CommandHandler, str]] = {
    "/help": (_cmd_help, "Show this help message"),
    "/exit": (_cmd_exit, "Exit the chat"),
    "/clear": (_cmd_clear, "Start a new conversation"),
    "/config": (_cmd_config, "Open the config panel"),
    "/connect": (_cmd_connect, "Connect a data source: /connect <source...> \\[--alias alias]"),
    "/disconnect": (_cmd_disconnect, "Disconnect: /disconnect \\[alias]"),
}

SLASH_COMMANDS = tuple(_COMMANDS)
