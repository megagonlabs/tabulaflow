from __future__ import annotations

from typing import Any, cast

import pytest
from rich.text import Text

import tabulaflow.app.commands as commands
from tabulaflow.app.commands import CommandResult, handle_command
from tabulaflow.app.session import SessionState


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
