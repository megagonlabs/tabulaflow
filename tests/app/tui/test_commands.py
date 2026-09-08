from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from rich.text import Text

import tabulaflow.app.tui.commands as commands
from tabulaflow.app.tui.commands import CommandResult, handle_command
from tabulaflow.app.session import AppSession
from tabulaflow.data.catalog import DEFAULT_DATA_SOURCE_DEFINITIONS


class _FakeRegistry:
    def __init__(self) -> None:
        self.connectors: dict[str, object] = {}

    def has(self, alias: str) -> bool:
        return alias in self.connectors

    def register(self, alias: str, connector: object) -> None:
        self.connectors[alias] = connector


class _FakeSession:
    def __init__(self) -> None:
        self.registry = _FakeRegistry()
        self.data_source_definitions = DEFAULT_DATA_SOURCE_DEFINITIONS
        self.data_dir = Path(".")
        self.conversation_reset = False
        self.events: list[str] = []

    def note_event(self, description: str) -> None:
        self.events.append(description)

    def reset_conversation(self) -> None:
        self.conversation_reset = True


async def test_handle_command_reports_unclosed_quote_as_user_error() -> None:
    result = await handle_command(
        "/connect 'neo4j+s://recommendations:recommendations@demo.neo4jlabs.com?database=recommendations",
        cast(AppSession, object()),
    )

    assert isinstance(result, CommandResult)
    assert isinstance(result.output, Text)
    assert result.output.plain == "Invalid command syntax: No closing quotation"


async def test_handle_command_dispatches_valid_shell_quoted_command(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_args: list[str] | None = None

    async def fake_handler(args: list[str], _session: AppSession) -> CommandResult:
        nonlocal seen_args
        seen_args = args
        return CommandResult()

    monkeypatch.setitem(commands._COMMANDS, "/fake", (fake_handler, "Fake command"))

    result = await handle_command("/fake 'path with spaces.csv' alias", cast(AppSession, object()))

    assert isinstance(result, CommandResult)
    assert seen_args == ["path with spaces.csv", "alias"]


async def test_handle_command_escapes_unknown_command_markup() -> None:
    result = await handle_command("/[/]", cast(AppSession, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Unknown command: /[/]. Type /help for available commands."


async def test_clear_starts_a_new_conversation() -> None:
    session = _FakeSession()

    result = await handle_command("/clear", cast(AppSession, session))

    assert result.action == "clear"
    assert session.conversation_reset is True


async def test_connect_rejects_duplicate_alias_option() -> None:
    result = await handle_command(
        "/connect duckdb:///tmp/a.duckdb --alias first --alias second",
        cast(AppSession, _FakeSession()),
    )

    assert isinstance(result.output, Text)
    assert result.output.plain == "Invalid /connect syntax: --alias may only be provided once"


async def test_connect_rejects_invalid_alias() -> None:
    result = await handle_command("/connect ./sales.csv --alias bad-alias", cast(AppSession, _FakeSession()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Invalid /connect syntax: alias may contain only letters, digits, and underscores"


async def test_disconnect_rejects_extra_args() -> None:
    result = await handle_command("/disconnect sales extra", cast(AppSession, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Usage: /disconnect <alias>"


async def test_connect_registers_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    connector = object()

    async def fake_connect_data_source(_source: object, **_kwargs: object) -> object:
        return connector

    monkeypatch.setattr(commands, "connect_data_source", fake_connect_data_source)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "test connector")

    result = await handle_command(
        "/connect postgres://alice:secret@example.com:5432/app --alias sales",
        cast(AppSession, session),
    )

    assert isinstance(result.output, Text)
    assert result.output.plain == "✓ Connected to sales (test connector)"
    assert session.registry.connectors == {"sales": connector}


async def test_connect_allows_same_source_under_distinct_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()

    async def fake_connect_data_source(_source: object, **_kwargs: object) -> object:
        return object()

    monkeypatch.setattr(commands, "connect_data_source", fake_connect_data_source)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "test connector")

    first = await handle_command(
        "/connect postgres://example.com/app --alias primary",
        cast(AppSession, session),
    )
    second = await handle_command(
        "/connect postgres://example.com/app --alias reference",
        cast(AppSession, session),
    )

    assert isinstance(first.output, Text)
    assert isinstance(second.output, Text)
    assert set(session.registry.connectors) == {"primary", "reference"}


async def test_connect_catalog_source_uses_default_alias_and_announces_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    connector = object()

    async def fake_connect_data_source(_source: object, **_kwargs: object) -> object:
        return connector

    monkeypatch.setattr(commands, "connect_data_source", fake_connect_data_source)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "sparql")

    result = await handle_command("/connect wikidata", cast(AppSession, session))

    assert isinstance(result.output, Text)
    assert result.output.plain == "✓ Connected to wikidata (sparql)"
    assert session.registry.connectors == {"wikidata": connector}
    assert "en,mul" in session.events[-1]
    assert "get_db_document" in session.events[-1]


async def test_connect_generated_alias_is_suffixed_on_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    session.registry.connectors["wikidata"] = object()

    async def fake_connect_data_source(_source: object, **_kwargs: object) -> object:
        return object()

    monkeypatch.setattr(commands, "connect_data_source", fake_connect_data_source)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "sparql")

    await handle_command("/connect wikidata", cast(AppSession, session))

    assert set(session.registry.connectors) == {"wikidata", "wikidata_2"}
