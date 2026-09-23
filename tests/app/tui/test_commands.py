from __future__ import annotations

from pathlib import Path
import shlex
from typing import cast

import pytest
from rich.text import Text

import tabulaflow.app.tui.commands as commands
from tabulaflow.app.tui.commands import (
    CommandResult,
    complete_hf_subset_selection,
    handle_command,
    redact_command_credentials,
)
from tabulaflow.app.session import AppSession
from tabulaflow.data.catalog import DEFAULT_DATA_SOURCE_DEFINITIONS, WIKIDATA_DESCRIPTION
from tabulaflow.data.config import DataSourceConnectorConfigs
from tabulaflow.data.loaders import HuggingFaceSubsetRequiredError


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
        self.connector_configs = DataSourceConnectorConfigs()
        self.data_dir = Path(".")
        self.conversation_reset = False
        self.events: list[str] = []

    def note_event(self, description: str) -> None:
        self.events.append(description)

    def reset_conversation(self) -> None:
        self.conversation_reset = True


def test_redact_connect_command_password_preserves_replayable_structure() -> None:
    command = "/connect 'neo4j+s://alice:p%40ss@example.com?database=neo4j' --alias graph"

    redacted, contains_credentials = redact_command_credentials(command)

    assert contains_credentials is True
    assert "p%40ss" not in redacted
    assert "alice:***@example.com" in redacted
    assert shlex.split(redacted)[-2:] == ["--alias", "graph"]


def test_redact_invalid_connect_command_hides_arguments() -> None:
    redacted, contains_credentials = redact_command_credentials("/connect 'neo4j://alice:secret@example.com")

    assert redacted == "/connect [invalid arguments hidden]"
    assert contains_credentials is True


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


async def test_connect_requests_a_huggingface_subset_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()

    async def require_subset(_source: object, **_kwargs: object) -> object:
        raise HuggingFaceSubsetRequiredError("nyu-mll/glue", ["cola", "mnli", "mrpc"])

    monkeypatch.setattr(commands, "connect_data_source", require_subset)

    result = await handle_command(
        "/connect https://huggingface.co/datasets/nyu-mll/glue --alias glue",
        cast(AppSession, session),
    )

    assert isinstance(result.action, commands.HuggingFaceSubsetSelection)
    assert result.action.alias == "glue"
    assert result.action.dataset_id == "nyu-mll/glue"
    assert result.action.subsets == ("cola", "mnli", "mrpc")
    assert session.registry.connectors == {}


async def test_huggingface_subset_choice_resumes_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    connector = object()
    sources: list[object] = []

    async def fake_connect_data_source(source: object, **_kwargs: object) -> object:
        sources.append(source)
        if source == "https://huggingface.co/datasets/nyu-mll/glue":
            raise HuggingFaceSubsetRequiredError("nyu-mll/glue", ["cola", "mnli", "mrpc"])
        return connector

    monkeypatch.setattr(commands, "connect_data_source", fake_connect_data_source)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "test connector")
    initial = await handle_command(
        "/connect https://huggingface.co/datasets/nyu-mll/glue --alias glue",
        cast(AppSession, session),
    )
    assert isinstance(initial.action, commands.HuggingFaceSubsetSelection)

    result = await complete_hf_subset_selection(initial.action, "mrpc", cast(AppSession, session))

    assert sources[-1] == "https://huggingface.co/datasets/nyu-mll/glue/viewer/mrpc"
    assert isinstance(result.output, Text)
    assert result.output.plain == "✓ Connected to glue (test connector)"
    assert session.registry.connectors == {"glue": connector}


async def test_connect_error_redacts_password_from_source(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(_source: object, **_kwargs: object) -> object:
        raise RuntimeError("authentication failed")

    monkeypatch.setattr(commands, "connect_data_source", fail)

    result = await handle_command(
        "/connect 'neo4j+s://alice:p%40ss@example.com' --alias graph",
        cast(AppSession, _FakeSession()),
    )

    assert isinstance(result.output, Text)
    assert "p%40ss" not in result.output.plain
    assert "neo4j+s://alice:***@example.com" in result.output.plain
    assert "authentication failed" in result.output.plain


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
    assert WIKIDATA_DESCRIPTION.strip() in session.events[-1]
    assert "get_data_source_document" in session.events[-1]


async def test_connect_generated_alias_is_suffixed_on_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    session.registry.connectors["wikidata"] = object()

    async def fake_connect_data_source(_source: object, **_kwargs: object) -> object:
        return object()

    monkeypatch.setattr(commands, "connect_data_source", fake_connect_data_source)
    monkeypatch.setattr(commands, "format_connector_summary", lambda _connector: "sparql")

    await handle_command("/connect wikidata", cast(AppSession, session))

    assert set(session.registry.connectors) == {"wikidata", "wikidata_2"}
