from __future__ import annotations

from typing import Any, cast

import pytest
from rich.text import Text

import tabulaflow.app.commands as commands
from tabulaflow.app.commands import CommandResult, handle_command
from tabulaflow.app.session import SessionState


class _FakeRegistry:
    def has(self, _alias: str) -> bool:
        return False


class _FakeSession:
    def __init__(self) -> None:
        self.registry = _FakeRegistry()
        self.source_key: object | None = None

    def find_alias_by_source(self, _key: object) -> str | None:
        return None

    def register_db(self, _alias: str, _connector: object, source_key: object) -> None:
        self.source_key = source_key

    def note_event(self, _description: str) -> None:
        pass


@pytest.mark.asyncio
async def test_handle_command_reports_unclosed_quote_as_user_error() -> None:
    result = await handle_command(
        "/connect 'neo4j+s://recommendations:recommendations@demo.neo4jlabs.com?database=recommendations",
        cast(SessionState, object()),
    )

    assert isinstance(result, CommandResult)
    assert isinstance(result.output, Text)
    assert result.output.plain == "Invalid command syntax: No closing quotation"


@pytest.mark.asyncio
async def test_handle_command_dispatches_valid_shell_quoted_command(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_args: list[str] | None = None

    async def fake_handler(args: list[str], _session: SessionState) -> CommandResult:
        nonlocal seen_args
        seen_args = args
        return CommandResult()

    monkeypatch.setitem(cast(Any, commands.COMMANDS), "/fake", fake_handler)

    result = await handle_command("/fake 'path with spaces.csv' alias", cast(SessionState, object()))

    assert isinstance(result, CommandResult)
    assert seen_args == ["path with spaces.csv", "alias"]


@pytest.mark.asyncio
async def test_handle_command_escapes_unknown_command_markup() -> None:
    result = await handle_command("/[/]", cast(SessionState, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Unknown command: /[/]. Type /help for available commands."


@pytest.mark.asyncio
async def test_connect_rejects_extra_url_args() -> None:
    result = await handle_command("/connect duckdb:///tmp/a.duckdb alias extra", cast(SessionState, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Usage: /connect <url_or_path> [alias]"


@pytest.mark.asyncio
async def test_connect_rejects_extra_file_aliases() -> None:
    result = await handle_command("/connect ./sales.csv alias extra", cast(SessionState, _FakeSession()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Usage: /connect <file...> [alias]"


@pytest.mark.asyncio
async def test_disconnect_rejects_extra_args() -> None:
    result = await handle_command("/disconnect sales extra", cast(SessionState, object()))

    assert isinstance(result.output, Text)
    assert result.output.plain == "Usage: /disconnect <alias>"


@pytest.mark.asyncio
async def test_connect_source_key_strips_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()

    async def fake_connect_url(_url: str, **_kwargs: object) -> object:
        return object()

    monkeypatch.setattr(commands, "connect_url", fake_connect_url)
    monkeypatch.setattr(commands, "connector_info", lambda _connector: "test connector")

    result = await handle_command(
        "/connect postgres://alice:secret@example.com:5432/app sales",
        cast(SessionState, session),
    )

    assert isinstance(result.output, Text)
    assert result.output.plain == "✓ Connected to sales (test connector)"
    assert session.source_key == ("url", "postgresql+asyncpg://example.com:5432/app")
