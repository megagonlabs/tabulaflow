"""Persistent store for user messages and tool responses, with overflow truncation.

Every user prompt and tool response is mirrored into ``workspace._internal.messages``
as a single row. Every model-visible response carries a leading ``[message_id=M<n>]``
marker so the agent can dereference it programmatically. When content exceeds
``MESSAGE_THRESHOLD_CHARS``, the body is additionally replaced with a head + tail
snippet that points back at the stored row; the agent retrieves the full text via SQL
on the workspace database.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pydantic_ai.capabilities.abstract import AbstractCapability
from pydantic_ai.messages import ToolReturn

if TYPE_CHECKING:
    from pydantic_ai import RunContext
    from pydantic_ai.messages import ToolCallPart
    from pydantic_ai.tools import ToolDefinition

    from tabulaflow.core.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

MESSAGE_THRESHOLD_CHARS = 8192 * 4
MESSAGE_HEAD_CHARS = 4096 * 4
MESSAGE_TAIL_CHARS = 1024 * 4

_SCHEMA = "_internal"
_TABLE = "messages"
_QUALIFIED = f'"{_SCHEMA}"."{_TABLE}"'

MessageKind = Literal["user_prompt", "tool_return"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def id_marker(message_id: str) -> str:
    """Return the leading ``[message_id=M<n>]`` line that tags every stored response.

    Present on both truncated snippets and full passthrough responses so the agent
    can always parse the id from the first line and dereference it programmatically.
    """
    return f"[message_id={message_id}]"


def make_marked(message_id: str, content: str) -> str:
    """Return full ``content`` prefixed with its id marker (no truncation)."""
    return f"{id_marker(message_id)}\n{content}"


def make_snippet(message_id: str, content: str) -> str:
    """Return the head+tail snippet shown to the LLM for an overflowed message.

    The marker is self-describing: it names the ``run_query`` call (with the
    ``workspace`` alias and a schema-qualified table) that fetches the full
    content, so a reader needs no out-of-band instructions to dereference it.
    """
    total = len(content)
    head = content[:MESSAGE_HEAD_CHARS]
    tail = content[-MESSAGE_TAIL_CHARS:] if total > MESSAGE_HEAD_CHARS + MESSAGE_TAIL_CHARS else ""
    deref = f"run_query(db_alias=\"workspace\", \"SELECT content FROM {_SCHEMA}.{_TABLE} WHERE message_id='{message_id}'\")"
    marker = f"... [truncated, {total} chars total — read full content with {deref}]"
    parts = [id_marker(message_id), head, marker]
    if tail:
        parts.append(tail)
    return "\n".join(parts)


class MessageStore:
    """Append-only mirror of user prompts and tool responses in workspace DuckDB.

    The store assigns sequential ``M1``, ``M2``, ... ids and persists every entry
    even when it is below the truncation threshold so the agent can SQL-introspect
    the conversation. The model-visible truncation logic lives separately
    (``ChatAgent.run`` for user prompts; ``MessageStoreCapability`` for tool returns).
    """

    def __init__(self, *, spill_connector: SQLConnector | None = None) -> None:
        self._spill_connector = spill_connector
        self._next_id = 1
        self._table_created = False
        self._lock = asyncio.Lock()

    def attach_connector(self, connector: SQLConnector) -> None:
        """Bind a workspace connector after construction (mirrors QueryHistory)."""
        self._spill_connector = connector
        self._table_created = False

    async def add(
        self,
        *,
        kind: MessageKind,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Persist one message and return its assigned id (e.g. ``"M7"``).

        ``agent_id`` is a provenance tag (e.g. ``"main"``, ``"subagent:<call>:<row>"``)
        — not an access scope. Use :meth:`scoped` to bind it once and avoid threading
        the value through every call site.
        """
        async with self._lock:
            message_id = f"M{self._next_id}"
            self._next_id += 1
        if self._spill_connector is None:
            return message_id
        try:
            await self._ensure_table()
            await self._insert_row(
                message_id=message_id,
                agent_id=agent_id,
                kind=kind,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                created_at=_utcnow(),
                char_len=len(content),
                content=content,
            )
        except Exception:
            logger.warning("Failed to persist message %s to workspace", message_id, exc_info=True)
        return message_id

    def scoped(self, agent_id: str) -> ScopedMessageStore:
        """Return a thin handle that pins ``agent_id`` on every ``add`` call."""
        return ScopedMessageStore(_store=self, agent_id=agent_id)

    async def _ensure_table(self) -> None:
        if self._table_created or self._spill_connector is None:
            return
        await self._spill_connector.run_query_async(f'CREATE SCHEMA IF NOT EXISTS "{_SCHEMA}"')
        await self._spill_connector.run_query_async(
            f"""
            CREATE TABLE IF NOT EXISTS {_QUALIFIED} (
                message_id   TEXT PRIMARY KEY,
                agent_id     TEXT,
                kind         TEXT NOT NULL,
                tool_name    TEXT,
                tool_call_id TEXT,
                created_at   TIMESTAMP NOT NULL,
                char_len     INTEGER NOT NULL,
                content      TEXT NOT NULL
            )
            """.strip()
        )
        self._table_created = True

    async def _insert_row(
        self,
        *,
        message_id: str,
        agent_id: str | None,
        kind: MessageKind,
        tool_name: str | None,
        tool_call_id: str | None,
        created_at: datetime,
        char_len: int,
        content: str,
    ) -> None:
        import pandas as pd

        assert self._spill_connector is not None
        df = pd.DataFrame(
            [
                {
                    "message_id": message_id,
                    "agent_id": agent_id,
                    "kind": kind,
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "created_at": created_at,
                    "char_len": char_len,
                    "content": content,
                }
            ]
        )
        await self._spill_connector.write_dataframe_async(df=df, table_name=_TABLE, schema_name=_SCHEMA, mode="append")


@dataclass
class ScopedMessageStore:
    """A thin handle over :class:`MessageStore` that pins ``agent_id`` on writes.

    Provenance tagging only — does not restrict reads in any way. Construct via
    :meth:`MessageStore.scoped` rather than instantiating directly.
    """

    _store: MessageStore
    agent_id: str

    async def add(
        self,
        *,
        kind: MessageKind,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> str:
        return await self._store.add(
            kind=kind,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            agent_id=self.agent_id,
        )


@dataclass
class MessageStoreCapability(AbstractCapability[Any]):
    """Mirror tool responses into the message store; tag every one and truncate overflow.

    Only tools whose names appear in ``tool_allowlist`` are subject to the flow. Each
    allowlisted string response is persisted and returned with a ``[message_id=M<n>]``
    marker (plus ``message_id``/``char_len`` metadata); responses over
    ``threshold_chars`` also have their body replaced with a head + tail snippet. Tools
    outside the allowlist (e.g. ``run_query``, which the agent uses to read back stored
    messages) pass through untouched — crucial to avoid re-truncation cycles when the
    agent fetches a stored message.
    """

    store: ScopedMessageStore
    tool_allowlist: frozenset[str]
    threshold_chars: int = MESSAGE_THRESHOLD_CHARS

    async def after_tool_execute(
        self,
        ctx: RunContext[Any],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: Any,
        result: Any,
    ) -> Any:
        if tool_def.name not in self.tool_allowlist:
            return result
        if not isinstance(result, str):
            return result
        message_id = await self.store.add(
            kind="tool_return",
            content=result,
            tool_name=tool_def.name,
            tool_call_id=call.tool_call_id,
        )
        if len(result) <= self.threshold_chars:
            return_value = make_marked(message_id, result)
        else:
            return_value = make_snippet(message_id, result)
        return ToolReturn(
            return_value=return_value,
            metadata={"message_id": message_id, "char_len": len(result)},
        )
