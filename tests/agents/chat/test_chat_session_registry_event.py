from typing import Any, cast

import pytest
from tabulaflow.agents.chat.session import ChatSession
from tabulaflow.core import (
    NodeSchema,
    PropertyGraphSchema,
    RelationshipEndpoint,
    RelationshipSchema,
    SQLSchema,
    SQLTableSchema,
)
from tabulaflow.data import DataConnectorRegistry


class FakeSQLConnector:
    backend = "sqlite"
    global_id = "fake+sql"
    schema = SQLSchema(
        display_name="test",
        dialect="sqlite",
        tables=[
            SQLTableSchema(name="a", is_view=False, columns=[], primary_key=[], foreign_keys=[]),
            SQLTableSchema(name="b", is_view=False, columns=[], primary_key=[], foreign_keys=[]),
        ],
    )

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
    global_id = "fake+graph"
    schema = PropertyGraphSchema(
        display_name="test",
        nodes=[NodeSchema(label="Person")],
        relationships=[
            RelationshipSchema(
                label="KNOWS",
                endpoints=[
                    RelationshipEndpoint(source_label="Person", target_label="Person"),
                    RelationshipEndpoint(source_label="Person", target_label="Organization"),
                ],
            )
        ],
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

    registry = DataConnectorRegistry()
    registry.register("sales", cast(Any, FakeSQLConnector()))
    registry.register("graph", cast(Any, FakeGraphConnector()))

    agent = ChatSession(registry=registry, model="test:model", reasoning="low")

    assert len(agent._context_messages) == 2
    assert str(cast(Any, agent._context_messages[0].parts[0]).content) == (
        "[system: the model powering this conversation is Model.]"
    )
    message = agent._context_messages[1]
    event = str(cast(Any, message.parts[0]).content)
    assert event.startswith("[system: the following data sources are already registered:")
    assert "`sales` (sqlite, 2 tables)" in event
    assert "`graph` (neo4j, cypher, 1 label, 1 relationship type)" in event
