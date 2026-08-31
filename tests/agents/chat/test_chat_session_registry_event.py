from types import SimpleNamespace
from typing import Any, cast

import pytest
from tabulaflow.agents.chat.session import ChatSession
from tabulaflow.data import DBRegistry


class FakeSQLConnector:
    connector_type = "sql"
    backend = "sqlite"
    global_id = "fake+sql"
    schema = SimpleNamespace(dialect="sqlite", tables=[object(), object()])

    @property
    def language(self) -> str:
        return "sqlite"

    async def run_query_async(self, *_args: Any, **_kwargs: Any) -> None:
        raise NotImplementedError

    async def close_async(self) -> None:
        pass

    async def refresh_schema_async(self) -> object:
        return self.schema


class FakeGraphConnector:
    connector_type = "property_graph"
    global_id = "fake+graph"
    schema = SimpleNamespace(
        nodes=[object()],
        relationships=[SimpleNamespace(endpoints=[object(), object()])],
    )

    @property
    def backend(self) -> str:
        return "neo4j"

    @property
    def language(self) -> str:
        return "cypher"

    async def run_query_async(self, *_args: Any, **_kwargs: Any) -> None:
        raise NotImplementedError

    async def close_async(self) -> None:
        pass

    async def refresh_schema_async(self) -> object:
        return self.schema


def test_chat_session_notes_pre_registered_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    def skip_agent_build(self: ChatSession, model: str) -> None:
        return None

    monkeypatch.setattr(ChatSession, "_make_agent", skip_agent_build)

    registry = DBRegistry()
    registry.register("sales", cast(Any, FakeSQLConnector()))
    registry.register("graph", cast(Any, FakeGraphConnector()))

    agent = ChatSession(registry=registry, model="test:model", reasoning="low")

    assert len(agent._message_history) == 2
    assert str(cast(Any, agent._message_history[0].parts[0]).content) == (
        "[system: the model powering this conversation is Model.]"
    )
    message = agent._message_history[1]
    event = str(cast(Any, message.parts[0]).content)
    assert event.startswith("[system: the following data sources are already registered:")
    assert "`sales` (sqlite, 2 tables)" in event
    assert "`graph` (neo4j, cypher, 1 label, 1 relationship type)" in event
