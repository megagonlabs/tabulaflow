"""Per-session app state — the DB registry, chat agent, workspace, and the
source-alias bookkeeping that the slash commands operate on."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

WORKSPACE_ALIAS = "workspace"


async def create_duckdb_connector(db_path: Path, alias: str, *, read_only: bool = False) -> SQLConnector:
    """Create a DuckDB-backed connector at ``db_path`` registered as ``alias``.

    Opening a non-existent path read-write creates the (empty) database file, and the
    returned connector is the live connection — there is no separate create-then-connect
    step. Backs both the session workspace and agent-built writable datasets. Schema and
    query caching are off: these databases are mutable, so a cached schema would go stale
    as tables/rows are added.

    Async, so the caller builds it before the (synchronous) ``SessionState`` — the
    connector is handed to the session/agent at construction rather than attached
    afterwards."""
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

    db_path.parent.mkdir(parents=True, exist_ok=True)
    abspath = os.path.abspath(db_path)
    return await SQLConnector.from_url_async(
        global_id=f"cli+{alias}",
        url=f"duckdb:///{abspath}",
        db_name=alias,
        read_only=read_only,
        enable_schema_caching=False,
        enable_query_caching=False,
    )


async def create_workspace_connector(workspace_db_path: Path) -> SQLConnector:
    """Create the per-session workspace DuckDB connector at ``workspace_db_path``."""
    return await create_duckdb_connector(workspace_db_path, WORKSPACE_ALIAS, read_only=False)


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
        reasoning_effort: str,
        project_dir: Path | None = None,
        scratch_dir: Path | None = None,
    ) -> None:
        from tabulaflow.chat import ChatAgent
        from tabulaflow.core.db_connector.db_registry import DBRegistry

        self.agent_name = agent
        self.session_id = session_id
        self.data_dir = data_dir
        # The directory the app was launched from (where the user's source data
        # lives) and the agent's transient working area. Handed to the agent so its
        # forthcoming shell/dataset tools resolve source reads against the project and
        # stage intermediates under scratch.
        self.project_dir = project_dir
        self.scratch_dir = scratch_dir
        self.registry: DBRegistry = DBRegistry()
        if workspace is not None:
            self.registry.register(WORKSPACE_ALIAS, workspace)
        self.chat_agent: ChatAgent = ChatAgent(
            registry=self.registry,
            model=model,
            reasoning_effort=reasoning_effort,
            workspace=workspace,
            trajectory_log_dir=trajectories_dir,
            project_dir=project_dir,
            scratch_dir=scratch_dir,
            create_dataset_fn=self.create_dataset,
        )
        self.last_result: object | None = None
        # Maps a "what's this connection's source" key (frozenset of file
        # paths, normalized URL, etc.) to the alias under which it is
        # registered.  Used by ``/connect`` to detect duplicate sources
        # being registered under different aliases.
        self._sources: dict[object, str] = {}

    async def create_dataset(self, name: str) -> str:
        """Create a writable dataset on behalf of the agent; return its alias.

        Bound and handed to the chat agent as a host callback so its ``create_dataset``
        tool can register a new source through the same path as the slash commands."""
        from tabulaflow.app.commands import create_dataset as _create_dataset

        return await _create_dataset(self, name)

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

    @property
    def reasoning_effort(self) -> str:
        return self.chat_agent.reasoning_effort

    def set_reasoning_effort(self, reasoning_effort: str) -> None:
        self.chat_agent.set_reasoning_effort(reasoning_effort)
