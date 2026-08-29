"""ToolCallOutcome metadata rides each LLM-facing tool return, keyed to its own call."""

from pathlib import Path

import pytest
import sqlalchemy
from pydantic_ai import ToolReturn
from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart
from sqlalchemy.ext.asyncio import create_async_engine

from tabulaflow.agents.chat.turn import _TextStreamRouter, _emit_stream_event
from tabulaflow.agents.chat.events import ChatEvent, ToolFinished
from tabulaflow.data.registry import DBRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter
from tabulaflow.output.store import OutputStore
from tabulaflow.agents.tools import (
    RegistryGetColumnJsonSchemaTool,
    RegistryGetDBDocumentTool,
    RegistryGetSchemaTool,
    RegistryGetTableSchemaTool,
    RegistryRunQueryTool,
    TransferSourceTableTool,
    ToolCallOutcome,
)


async def _make_connector(tmp_path: Path) -> SQLConnector:
    db_path = tmp_path / "db.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE TABLE t (a TEXT, b INTEGER);"))
        await conn.execute(sqlalchemy.text("INSERT INTO t VALUES ('x', 1), ('y', 2), ('z', 3);"))
    await engine.dispose()
    return await SQLConnector.from_url_async(
        global_id="test_outcome", url=f"sqlite+aiosqlite:///{db_path}", db_name="db"
    )


@pytest.fixture
async def registry(tmp_path: Path) -> DBRegistry:
    r = DBRegistry()
    r.register("mydb", await _make_connector(tmp_path))
    return r


class TestRunQueryOutcome:
    async def test_success_reports_rows(self, registry: DBRegistry) -> None:
        result = await RegistryRunQueryTool(registry)("mydb", "SELECT * FROM t")
        assert isinstance(result, ToolReturn)
        assert isinstance(result.return_value, str) and result.return_value.startswith("[source_id=")
        assert result.metadata == ToolCallOutcome(count=3, unit="rows")

    async def test_query_error_reports_error(self, registry: DBRegistry) -> None:
        result = await RegistryRunQueryTool(registry)("mydb", "SELECT * FROM missing")
        assert isinstance(result, ToolReturn)
        assert result.metadata == ToolCallOutcome(error=True)

    async def test_unknown_alias_reports_error(self, registry: DBRegistry) -> None:
        result = await RegistryRunQueryTool(registry)("nope", "SELECT 1")
        assert isinstance(result, ToolReturn)
        assert result.metadata == ToolCallOutcome(error=True)

    async def test_programmatic_call_returns_text(self, registry: DBRegistry) -> None:
        result = await RegistryRunQueryTool(registry)("mydb", "SELECT * FROM t")
        assert isinstance(result, ToolReturn)
        assert isinstance(result.return_value, str) and result.return_value.startswith("[source_id=")


class TestGetTableSchemaOutcome:
    async def test_success_reports_columns(self, registry: DBRegistry) -> None:
        tool = RegistryGetTableSchemaTool(registry, SQLDDLSchemaFormatter())
        result = await tool("mydb", None, "t")
        assert isinstance(result, ToolReturn)
        assert result.metadata == ToolCallOutcome(count=2, unit="columns")

    async def test_missing_table_reports_no_count(self, registry: DBRegistry) -> None:
        tool = RegistryGetTableSchemaTool(registry, SQLDDLSchemaFormatter())
        result = await tool("mydb", None, "missing")
        assert isinstance(result, ToolReturn)
        assert result.metadata == ToolCallOutcome(error=True)


class TestRegistryToolErrorOutcomes:
    async def test_column_json_schema_error_has_metadata(self) -> None:
        result = await RegistryGetColumnJsonSchemaTool(DBRegistry())("missing", None, "t", "payload")
        assert result.metadata == ToolCallOutcome(error=True)

    async def test_db_document_error_has_metadata(self) -> None:
        tool = RegistryGetDBDocumentTool(DBRegistry(), db_summarizer_cls=lambda **_: None)
        result = await tool("missing")
        assert result.metadata == ToolCallOutcome(error=True)

    async def test_schema_error_has_metadata(self) -> None:
        result = await RegistryGetSchemaTool(DBRegistry())("missing")
        assert result.metadata == ToolCallOutcome(error=True)

    async def test_transfer_error_has_metadata(self) -> None:
        result = await TransferSourceTableTool(DBRegistry(), OutputStore())("S1", "workspace", None, "target")
        assert result.metadata == ToolCallOutcome(error=True)


class TestChatOutcomeNormalization:
    async def _finish_event(self, content: str, metadata: object = None) -> ToolFinished:
        events: list[ChatEvent] = []
        part = ToolReturnPart(tool_name="x", tool_call_id="c1", content=content, metadata=metadata)
        await _emit_stream_event(FunctionToolResultEvent(part=part), events.append, _TextStreamRouter())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ToolFinished)
        return event

    async def test_passes_metadata_through(self) -> None:
        outcome = ToolCallOutcome(count=3, unit="rows")
        event = await self._finish_event("ok", outcome)
        assert event.outcome == outcome

    async def test_falls_back_to_content_error_convention(self) -> None:
        event = await self._finish_event("(error: boom)")
        assert event.outcome == ToolCallOutcome(error=True)

    async def test_plain_completion_has_no_outcome(self) -> None:
        event = await self._finish_event("ok")
        assert event.outcome is None
