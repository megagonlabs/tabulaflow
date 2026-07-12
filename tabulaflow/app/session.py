"""Per-session app state — the DB registry, chat agent, workspace, and the
source-alias bookkeeping that the slash commands operate on."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulaflow.core.db_connector.base import NL2QDBConnector
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
        # Mutable store: a cached schema would go stale as tables/rows change.
        enable_schema_caching=False,
        enable_query_caching=False,
    )


class SessionState:
    """Holds state for a single interactive session."""

    def __init__(
        self,
        model: str,
        session_id: str,
        trajectories_dir: Path,
        data_dir: Path,
        workspace: SQLConnector | None,
        reasoning_effort: str,
        project_dir: Path | None = None,
        scratch_dir: Path | None = None,
        subagent_model: str = "openai-responses:gpt-5.4-mini",
        subagent_reasoning_effort: str = "medium",
    ) -> None:
        from tabulaflow.chat import ChatAgent
        from tabulaflow.core.db_connector.db_registry import DBRegistry

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
            subagent_model=subagent_model,
            subagent_reasoning_effort=subagent_reasoning_effort,
            project_dir=project_dir,
            scratch_dir=scratch_dir,
            data_dir=data_dir,
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

    async def register_db(self, alias: str, connector: NL2QDBConnector, source_key: object) -> None:
        """Register a user-connected database, then drop the auto-loaded sample placeholder.

        The bundled ``sample_data`` DB auto-connects for first-run convenience; once the
        user connects real data it's removed so it can't be confused with (or queried in
        place of) the user's own data.
        """
        from tabulaflow.app.sample_data import SAMPLE_ALIAS

        self.registry.register(alias, connector)
        self.register_source(source_key, alias)

        if alias != SAMPLE_ALIAS and self.registry.has(SAMPLE_ALIAS):
            await self.registry.unregister_async(SAMPLE_ALIAS)
            self.unregister_alias_sources(SAMPLE_ALIAS)
            self.chat_agent.note_event(
                f"the bundled sample data `{SAMPLE_ALIAS}` has been removed now that the user "
                "connected their own data; disregard it from here on."
            )

    @property
    def model(self) -> str:
        return self.chat_agent.model

    def set_main_profile(self, *, model: str, reasoning_effort: str) -> None:
        self.chat_agent.set_main_profile(model=model, reasoning_effort=reasoning_effort)

    @property
    def api_key(self) -> str | None:
        return self.chat_agent.api_key

    @property
    def supported_efforts(self) -> tuple[str, ...]:
        return self.chat_agent.supported_efforts

    @property
    def reasoning_effort(self) -> str:
        return self.chat_agent.reasoning_effort

    @property
    def subagent_model(self) -> str:
        return self.chat_agent.subagent_model

    def set_subagent_profile(self, *, model: str, reasoning_effort: str) -> None:
        self.chat_agent.set_subagent_profile(model=model, reasoning_effort=reasoning_effort)

    @property
    def subagent_api_key(self) -> str | None:
        return self.chat_agent.subagent_api_key

    @property
    def subagent_supported_efforts(self) -> tuple[str, ...]:
        return self.chat_agent.subagent_supported_efforts

    @property
    def subagent_reasoning_effort(self) -> str:
        return self.chat_agent.subagent_reasoning_effort
