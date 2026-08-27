from __future__ import annotations

from typing import Any, cast

import pytest
from rich.text import Text

import tabulaflow.app.tui.commands as commands
from tabulaflow.app.tui.commands import CommandResult, handle_command
from tabulaflow.app.session import AppSession


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
        self.conversation_reset = False

    def note_event(self, _description: str) -> None:
        pass

    def reset_conversation(self) -> None:
        self.conversation_reset = True


@pytest.mark.asyncio
async def test_handle_command_reports_unclosed_quote_as_user_error() -> None:
    result = await handle_command(
        "/connect 'neo4j+s://recommendations:recommendations@demo.neo4jlabs.com?database=recommendations",
        cast(AppSession, object()),
    )

    assert isinstance(result, CommandResult)
    assert isinstance(result.output, Text)
    assert result.output.plain == "Invalid command syntax: No closing quotation"


@pytest.mark.asyncio
async def test_handle_command_dispatches_valid_shell_quoted_command(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_args: list[str] | None = None

    async def fake_handler(args: list[str], _session: AppSession) -> CommandResult:
        nonlocal seen_args
        seen_args = args
        return CommandResult()

    monkeypatch.setitem(cast(Any, commands.COMMANDS), "/fake", fake_handler)

    result = await handle_command("/fake 'path with spaces.csv' alias", cast(AppSession, object()))

    assert isinstance(result, CommandResult)
    assert seen_args == ["path with spaces.csv", "alias"]


@pytest.mark.asyncio
async def test_handle_command_escapes_unknown_command_markup() -> None:
    result = await handle_command("/[/]", cast(AppSession, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Unknown command: /[/]. Type /help for available commands."


@pytest.mark.asyncio
async def test_clear_starts_a_new_conversation() -> None:
    session = _FakeSession()

    result = await handle_command("/clear", cast(AppSession, session))

    assert result.should_clear is True
    assert session.conversation_reset is True


@pytest.mark.asyncio
async def test_connect_rejects_extra_url_args() -> None:
    result = await handle_command("/connect duckdb:///tmp/a.duckdb alias extra", cast(AppSession, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Usage: /connect <url_or_path> [alias]"


@pytest.mark.asyncio
async def test_connect_rejects_extra_file_aliases() -> None:
    result = await handle_command("/connect ./sales.csv alias extra", cast(AppSession, _FakeSession()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Usage: /connect <file...> [alias]"


@pytest.mark.asyncio
async def test_disconnect_rejects_extra_args() -> None:
    result = await handle_command("/disconnect sales extra", cast(AppSession, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Usage: /disconnect <alias>"


@pytest.mark.asyncio
async def test_connect_registers_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    connector = object()

    async def fake_connect_url(_url: str, **_kwargs: object) -> object:
        return connector

    monkeypatch.setattr(commands, "connect_url", fake_connect_url)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "test connector")

    result = await handle_command(
        "/connect postgres://alice:secret@example.com:5432/app sales",
        cast(AppSession, session),
    )

    assert isinstance(result.output, Text)
    assert result.output.plain == "✓ Connected to sales (test connector)"
    assert session.registry.connectors == {"sales": connector}


@pytest.mark.asyncio
async def test_connect_allows_same_source_under_distinct_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()

    async def fake_connect_url(_url: str, **_kwargs: object) -> object:
        return object()

    monkeypatch.setattr(commands, "connect_url", fake_connect_url)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "test connector")

    first = await handle_command(
        "/connect postgres://example.com/app primary",
        cast(AppSession, session),
    )
    second = await handle_command(
        "/connect postgres://example.com/app reference",
        cast(AppSession, session),
    )

    assert isinstance(first.output, Text)
    assert isinstance(second.output, Text)
    assert set(session.registry.connectors) == {"primary", "reference"}
