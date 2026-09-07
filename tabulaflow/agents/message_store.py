"""Lossless offloading for content that may exceed an agent's context window.

User prompts and string tool results can be stored in
``workspace._internal.messages`` and represented to the model by a short
``[message_id=M<n>]`` marker. Large values are reduced to a head-and-tail snippet
that includes the exact ``run_query`` call needed to retrieve the stored body. This
keeps prompts bounded without preventing the agent, document extractors, or nested
subagents from accessing the complete content later.

Storage is best-effort and fail-open. An id is returned only after its row has been
written successfully; without a workspace or after a write failure, callers keep the
original content unchanged. ``MessageStoreCapability`` applies this policy to
allowlisted string tool results, while user prompts opt in directly through a scoped
store. Scopes add agent provenance but do not restrict access.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

import sqlalchemy
from pydantic_ai.capabilities.abstract import AbstractCapability
from pydantic_ai.messages import ToolReturn

if TYPE_CHECKING:
    from pydantic_ai import RunContext
    from pydantic_ai.messages import ToolCallPart
    from pydantic_ai.tools import ToolDefinition

    from tabulaflow.data.sql import SQLConnector

logger = logging.getLogger(__name__)

MESSAGE_HEAD_CHARS = 4096 * 4
MESSAGE_TAIL_CHARS = 1024 * 4

# Truncate only once a snippet would actually shrink the payload. A message
# barely larger than head+tail, snippeted, keeps both windows whole and adds a
# marker — ending up *larger* than the original. The slack is the overflow we
# require before truncating is a net win (well above the marker's own size).
_SNIPPET_SLACK_CHARS = 4096
MESSAGE_THRESHOLD_CHARS = MESSAGE_HEAD_CHARS + MESSAGE_TAIL_CHARS + _SNIPPET_SLACK_CHARS

_SCHEMA = "_internal"
_TABLE = "messages"
_QUALIFIED = f'"{_SCHEMA}"."{_TABLE}"'
_MESSAGE_TABLE = sqlalchemy.table(
    _TABLE,
    sqlalchemy.column("message_id"),
    sqlalchemy.column("agent_id"),
    sqlalchemy.column("kind"),
    sqlalchemy.column("tool_name"),
    sqlalchemy.column("tool_call_id"),
    sqlalchemy.column("created_at"),
    sqlalchemy.column("char_len"),
    sqlalchemy.column("content"),
    schema=_SCHEMA,
)

MessageKind = Literal["user_prompt", "tool_return"]


def id_marker(message_id: str) -> str:
    """Return the leading ``[message_id=M<n>]`` line that tags every stored response.

    Present on both truncated snippets and full passthrough responses so the agent
    can always parse the id from the first line and dereference it programmatically.
    """
    return f"[message_id={message_id}]"


def make_marked(message_id: str, content: str) -> str:
    """Return full ``content`` prefixed with its id marker (no truncation)."""
    return f"{id_marker(message_id)}\n{content}"


def deref_call(message_id: str) -> str:
    """Return the ``run_query`` call that fetches a stored message's full content.

    Shared by every snippet builder so the dereference pointer (workspace alias,
    schema-qualified table) is written in exactly one place.
    """
    return f'run_query(connector_alias="workspace", "SELECT content FROM {_SCHEMA}.{_TABLE} WHERE message_id=\'{message_id}\'")'


def make_snippet(message_id: str, content: str) -> str:
    """Return the head+tail snippet shown to the LLM for an overflowed message.

    The marker is self-describing: it names the ``run_query`` call (with the
    ``workspace`` alias and a schema-qualified table) that fetches the full
    content, so a reader needs no out-of-band instructions to dereference it.
    """
    total = len(content)
    head = content[:MESSAGE_HEAD_CHARS]
    tail = content[-MESSAGE_TAIL_CHARS:] if total > MESSAGE_HEAD_CHARS + MESSAGE_TAIL_CHARS else ""
    marker = f"... [truncated, {total} chars total — read full content with {deref_call(message_id)}]"
    parts = [id_marker(message_id), head, marker]
    if tail:
        parts.append(tail)
    return "\n".join(parts)


class MessageStore:
    """Append-only mirror of user prompts and tool responses in workspace DuckDB.

    Successfully stored entries receive sequential ``M1``, ``M2``, ... ids. Model-
    visible marking and truncation remain the caller's responsibility.
    """

    def __init__(self, connector: SQLConnector | None = None) -> None:
        self._connector = connector
        self._next_id = 1
        self._table_created = False
        self._lock = asyncio.Lock()

    async def add(
        self,
        *,
        kind: MessageKind,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        agent_id: str | None = None,
    ) -> str | None:
        """Persist one message and return its id, or ``None`` if storage is unavailable.

        ``agent_id`` is a provenance tag (e.g. ``"main"``, ``"subagent:<call>:<row>"``)
        — not an access scope. Use :meth:`scoped` to bind it once and avoid threading
        the value through every call site.
        """
        connector = self._connector
        if connector is None:
            return None
        async with self._lock:
            message_id = f"M{self._next_id}"
            self._next_id += 1
        try:
            await self._ensure_table(connector)
            result = await connector.run_query_async(
                sqlalchemy.insert(_MESSAGE_TABLE).values(
                    message_id=message_id,
                    agent_id=agent_id,
                    kind=kind,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    created_at=datetime.now(timezone.utc),
                    char_len=len(content),
                    content=content,
                )
            )
            if result.error is not None:
                raise RuntimeError(result.error.message)
        except Exception:
            logger.warning("Failed to persist message %s to workspace", message_id, exc_info=True)
            return None
        return message_id

    def scoped(self, agent_id: str) -> ScopedMessageStore:
        """Return a thin handle that pins ``agent_id`` on every ``add`` call."""
        return ScopedMessageStore(_store=self, agent_id=agent_id)

    async def _ensure_table(self, connector: SQLConnector) -> None:
        if self._table_created:
            return
        statements = [
            f'CREATE SCHEMA IF NOT EXISTS "{_SCHEMA}"',
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
            """.strip(),
        ]
        for statement in statements:
            result = await connector.run_query_async(statement)
            if result.error is not None:
                raise RuntimeError(result.error.message)
        self._table_created = True


@dataclass(frozen=True)
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
    ) -> str | None:
        return await self._store.add(
            kind=kind,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            agent_id=self.agent_id,
        )


@dataclass
class MessageStoreCapability(AbstractCapability[Any]):
    """Store and mark allowlisted string tool results.

    Results are changed only after successful persistence: short results receive an id
    marker and oversized results are replaced by ``snippet_fn`` when truncation is
    enabled. Other tools, non-string results, and storage failures pass through unchanged.
    """

    store: ScopedMessageStore
    tool_allowlist: frozenset[str]
    threshold_chars: int = MESSAGE_THRESHOLD_CHARS
    truncate: bool = True
    snippet_fn: Callable[[str, str], str] = make_snippet

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
        if message_id is None:
            return result
        if not self.truncate or len(result) <= self.threshold_chars:
            return_value = make_marked(message_id, result)
        else:
            return_value = self.snippet_fn(message_id, result)
        return ToolReturn(
            return_value=return_value,
            metadata={"message_id": message_id, "char_len": len(result)},
        )
