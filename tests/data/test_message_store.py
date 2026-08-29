from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from tabulaflow.agents.message_store import MessageStore, MessageStoreCapability
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector


async def test_message_store_persists_and_returns_id(tmp_path: Path) -> None:
    connector = await SQLConnector.from_url_async(
        global_id="test-workspace",
        url=f"duckdb:///{tmp_path / 'workspace.duckdb'}",
        db_name="workspace",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )
    try:
        store = MessageStore(connector).scoped("main")

        message_id = await store.add(kind="user_prompt", content="hello")

        assert message_id == "M1"
        result = await connector.run_query_async(
            "SELECT message_id, agent_id, kind, char_len, content FROM _internal.messages"
        )
        assert result.error is None
        assert result.df is not None
        assert result.df.to_dict(orient="records") == [
            {
                "message_id": "M1",
                "agent_id": "main",
                "kind": "user_prompt",
                "char_len": 5,
                "content": "hello",
            }
        ]
    finally:
        await connector.close_async()


async def test_message_store_returns_none_without_connector() -> None:
    assert await MessageStore().add(kind="user_prompt", content="hello") is None


async def test_message_store_capability_preserves_content_when_storage_fails() -> None:
    capability = MessageStoreCapability(
        store=MessageStore().scoped("main"),
        tool_allowlist=frozenset({"browser_navigate"}),
        threshold_chars=1,
    )
    result = "full result"

    returned = await capability.after_tool_execute(
        cast(Any, None),
        call=cast(Any, SimpleNamespace(tool_call_id="call-1")),
        tool_def=cast(Any, SimpleNamespace(name="browser_navigate")),
        args={},
        result=result,
    )

    assert returned == result


async def test_message_store_returns_none_on_write_failure() -> None:
    class FailingConnector:
        async def run_query_async(self, _query: Any) -> Any:
            return SimpleNamespace(error=SimpleNamespace(message="write failed"))

    store = MessageStore(cast(SQLConnector, FailingConnector()))

    assert await store.add(kind="user_prompt", content="hello") is None
