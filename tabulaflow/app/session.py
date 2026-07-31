"""Per-session app state — DB registry, optional chat agent, and source aliases."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.config import LLMPreset

if TYPE_CHECKING:
    from tabulaflow.chat import ChatAgent
    from tabulaflow.core.db_connector.base import NL2QDBConnector
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

WORKSPACE_ALIAS = "workspace"
LLM_UNAVAILABLE_MESSAGE = "Select a preset in /config. /connect and browsing remain available."


async def create_workspace_connector(workspace_db_path: Path) -> SQLConnector:
    """Create the per-session workspace DuckDB connector at ``workspace_db_path``.

    Async, so the caller builds it before the (synchronous) ``SessionState`` — the
    connector is handed to the session/agent at construction rather than attached
    afterwards."""
    from tabulaflow.core.db_connector.sql_conn import SQLConnector
    from tabulaflow.toolhub import QUERY_HISTORY_SCHEMA

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
        # The agent spills every query result here, one table per record. Excluding it
        # keeps the data explorer and schema tools showing data rather than bookkeeping.
        exclude_schema_names=[QUERY_HISTORY_SCHEMA],
    )


class SessionState:
    """Holds state for a single interactive session."""

    def __init__(
        self,
        llm_preset: LLMPreset | None,
        trajectories_dir: Path,
        data_dir: Path,
        workspace: SQLConnector | None,
        service_tier: str | None = "priority",
        project_dir: Path | None = None,
        scratch_dir: Path | None = None,
    ) -> None:
        from tabulaflow.core.db_connector.db_registry import DBRegistry

        self.data_dir = data_dir
        self.llm_preset = llm_preset
        self._service_tier = service_tier
        self._trajectory_log_dir = trajectories_dir
        self._workspace = workspace
        # The directory the app was launched from (where the user's source data
        # lives) and the agent's transient working area. Handed to the agent so its
        # forthcoming shell/dataset tools resolve source reads against the project and
        # stage intermediates under scratch.
        self.project_dir = project_dir
        self.scratch_dir = scratch_dir
        self.registry: DBRegistry = DBRegistry()
        if workspace is not None:
            self.registry.register(WORKSPACE_ALIAS, workspace)
        self._chat_agent: ChatAgent | None = None
        # Maps a "what's this connection's source" key (frozenset of file
        # paths, normalized URL, etc.) to the alias under which it is
        # registered.  Used by ``/connect`` to detect duplicate sources
        # being registered under different aliases.
        self._sources: dict[object, str] = {}

    @property
    def active_chat_agent(self) -> ChatAgent | None:
        """Chat agent active for the selected preset, if initialized."""
        if self.llm_preset is None or not self._chat_agent_matches_preset(self.llm_preset):
            return None
        return self._chat_agent

    def _chat_agent_matches_preset(self, preset: LLMPreset) -> bool:
        agent = self._chat_agent
        return (
            agent is not None
            and agent.model == preset.main.model
            and agent.reasoning_effort == preset.main.reasoning_effort
            and agent.subagent_model == preset.subagent.model
            and agent.subagent_reasoning_effort == preset.subagent.reasoning_effort
        )

    def _build_chat_agent(
        self,
        *,
        preset: LLMPreset,
    ) -> ChatAgent:
        from tabulaflow.chat import ChatAgent

        return ChatAgent(
            registry=self.registry,
            model=preset.main.model,
            reasoning_effort=preset.main.reasoning_effort,
            service_tier=self._service_tier,
            workspace=self._workspace,
            trajectory_log_dir=self._trajectory_log_dir,
            subagent_model=preset.subagent.model,
            subagent_reasoning_effort=preset.subagent.reasoning_effort,
            project_dir=self.project_dir,
            scratch_dir=self.scratch_dir,
            data_dir=self.data_dir,
        )

    def activate_llm_preset(self, preset: LLMPreset) -> tuple[str | None, str | None]:
        """Construct or update the chat agent for ``preset`` and return its API keys.

        The caller owns selection state. Passing the preset explicitly keeps a
        superseded background activation from reading a newer selection midway
        through initialization.
        """
        if self._chat_agent is None:
            agent = self._build_chat_agent(preset=preset)
            keys = agent.resolve_api_keys()
            self._chat_agent = agent
            return keys
        elif not self._chat_agent_matches_preset(preset):
            return self._chat_agent.activate_llm_profile(
                model=preset.main.model,
                reasoning_effort=preset.main.reasoning_effort,
                subagent_model=preset.subagent.model,
                subagent_reasoning_effort=preset.subagent.reasoning_effort,
            )
        return self._chat_agent.resolve_api_keys()

    def note_event(self, description: str) -> None:
        """Append an app event to the chat agent when LLM support is available."""
        if self._chat_agent is not None:
            self._chat_agent.note_event(description)

    def find_alias_by_source(self, key: object) -> str | None:
        """Return the alias registered for ``key``, or None."""
        return self._sources.get(key)

    def register_source(self, key: object, alias: str) -> None:
        """Record that ``alias`` is associated with the source ``key``."""
        self._sources[key] = alias

    def unregister_alias_sources(self, alias: str) -> None:
        """Remove every source entry pointing at ``alias``."""
        self._sources = {k: v for k, v in self._sources.items() if v != alias}

    def register_db(self, alias: str, connector: NL2QDBConnector, source_key: object) -> None:
        """Register a user-connected database."""
        self.registry.register(alias, connector)
        self.register_source(source_key, alias)

    async def close(self) -> None:
        """Release session-owned runtime resources."""
        if self._chat_agent is not None:
            await self._chat_agent.aclose()
        await self.registry.disconnect_all_async()
