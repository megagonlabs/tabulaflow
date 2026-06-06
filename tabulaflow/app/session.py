"""Per-session app state — the DB registry, chat agent, workspace, and the
source-alias bookkeeping that the slash commands operate on."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

WORKSPACE_ALIAS = "workspace"


async def create_workspace_connector(workspace_db_path: Path) -> SQLConnector:
    """Create the per-session workspace DuckDB connector at ``workspace_db_path``.

    Async, so the caller builds it before the (synchronous) ``SessionState`` — the
    connector is handed to the session/agent at construction rather than attached
    afterwards."""
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

    workspace_db_path.parent.mkdir(parents=True, exist_ok=True)
    abspath = os.path.abspath(workspace_db_path)
    return await SQLConnector.from_url_async(
        global_id=f"cli+{WORKSPACE_ALIAS}",
        url=f"duckdb:///{abspath}",
        db_name=WORKSPACE_ALIAS,
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )


class SessionState:
    """Holds state for a single interactive session."""

    def __init__(
        self,
        model: str,
        agent: str,
        session_id: str,
        trajectories_dir: Path,
        data_dir: Path,
        workspace: SQLConnector | None,
    ) -> None:
        from tabulaflow.chat import ChatAgent
        from tabulaflow.core.db_connector.db_registry import DBRegistry

        self.agent_name = agent
        self.session_id = session_id
        self.data_dir = data_dir
        self.registry: DBRegistry = DBRegistry()
        if workspace is not None:
            self.registry.register(WORKSPACE_ALIAS, workspace)
        self.chat_agent: ChatAgent = ChatAgent(
            registry=self.registry,
            model=model,
            workspace=workspace,
            trajectory_log_dir=trajectories_dir,
        )
        self.last_result: object | None = None
        # Maps a "what's this connection's source" key (frozenset of file
        # paths, normalized URL, etc.) to the alias under which it is
        # registered.  Used by ``/connect`` to detect duplicate sources
        # being registered under different aliases.
        self._sources: dict[object, str] = {}

    def find_alias_by_source(self, key: object) -> str | None:
        """Return the alias registered for ``key``, or None."""
        return self._sources.get(key)

    def register_source(self, key: object, alias: str) -> None:
        """Record that ``alias`` is associated with the source ``key``."""
        self._sources[key] = alias

    def unregister_alias_sources(self, alias: str) -> None:
        """Remove every source entry pointing at ``alias``."""
        self._sources = {k: v for k, v in self._sources.items() if v != alias}

    @property
    def model(self) -> str:
        return self.chat_agent.model

    def set_model(self, model: str) -> None:
        self.chat_agent.set_model(model)
