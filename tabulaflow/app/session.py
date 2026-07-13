"""Per-session app state — DB registry, optional chat agent, and source aliases."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import os
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.config import LLMRoleConfig

if TYPE_CHECKING:
    from tabulaflow.chat import ChatAgent
    from tabulaflow.core.db_connector.base import NL2QDBConnector
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

WORKSPACE_ALIAS = "workspace"


@dataclass(frozen=True)
class ActiveLLMProfile:
    """Selected main/subagent LLM profile for the app session."""

    main: LLMRoleConfig
    subagent: LLMRoleConfig

    @classmethod
    def from_values(
        cls,
        *,
        model: str,
        reasoning_effort: str,
        subagent_model: str,
        subagent_reasoning_effort: str,
    ) -> ActiveLLMProfile:
        """Build a profile from CLI/session constructor values."""
        return cls(
            main=LLMRoleConfig.model_validate({"model": model, "reasoning_effort": reasoning_effort}),
            subagent=LLMRoleConfig.model_validate(
                {"model": subagent_model, "reasoning_effort": subagent_reasoning_effort}
            ),
        )


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
        service_tier: str | None = "priority",
        project_dir: Path | None = None,
        scratch_dir: Path | None = None,
        subagent_model: str = "openai-responses:gpt-5.4-mini",
        subagent_reasoning_effort: str = "medium",
    ) -> None:
        from tabulaflow.core.db_connector.db_registry import DBRegistry

        self.session_id = session_id
        self.data_dir = data_dir
        self.llm_profile = ActiveLLMProfile.from_values(
            model=model,
            reasoning_effort=reasoning_effort,
            subagent_model=subagent_model,
            subagent_reasoning_effort=subagent_reasoning_effort,
        )
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
        self.chat_agent: ChatAgent | None = None
        self.llm_error: str | None = None
        self._rebuild_chat_agent()
        self.last_result: object | None = None
        # Maps a "what's this connection's source" key (frozenset of file
        # paths, normalized URL, etc.) to the alias under which it is
        # registered.  Used by ``/connect`` to detect duplicate sources
        # being registered under different aliases.
        self._sources: dict[object, str] = {}

    @property
    def llm_available(self) -> bool:
        """Whether the selected LLM profile has a live chat agent."""
        return self.chat_agent is not None

    def _build_chat_agent(
        self,
        *,
        profile: ActiveLLMProfile,
    ) -> ChatAgent:
        from tabulaflow.chat import ChatAgent

        return ChatAgent(
            registry=self.registry,
            model=profile.main.model,
            reasoning_effort=profile.main.reasoning_effort,
            service_tier=self._service_tier,
            workspace=self._workspace,
            trajectory_log_dir=self._trajectory_log_dir,
            subagent_model=profile.subagent.model,
            subagent_reasoning_effort=profile.subagent.reasoning_effort,
            project_dir=self.project_dir,
            scratch_dir=self.scratch_dir,
            data_dir=self.data_dir,
        )

    def _rebuild_chat_agent(self) -> None:
        try:
            self.chat_agent = self._build_chat_agent(profile=self.llm_profile)
        except Exception as e:
            self.chat_agent = None
            self.llm_error = str(e)
        else:
            self.llm_error = None

    def note_event(self, description: str) -> None:
        """Append an app event to the chat agent when LLM support is available."""
        if self.chat_agent is not None:
            self.chat_agent.note_event(description)

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
            self.note_event(
                f"the bundled sample data `{SAMPLE_ALIAS}` has been removed now that the user "
                "connected their own data; disregard it from here on."
            )

    @property
    def model(self) -> str:
        return self.llm_profile.main.model

    @property
    def api_key(self) -> str | None:
        return self.chat_agent.api_key if self.chat_agent is not None else None

    @property
    def supported_efforts(self) -> tuple[str, ...]:
        return self.chat_agent.supported_efforts if self.chat_agent is not None else ()

    @property
    def reasoning_effort(self) -> str:
        return self.llm_profile.main.reasoning_effort

    @property
    def subagent_model(self) -> str:
        return self.llm_profile.subagent.model

    def set_llm_profile(self, profile: ActiveLLMProfile) -> None:
        """Atomically switch the selected LLM profile, raising if it cannot run."""
        old_profile = self.llm_profile
        old_agent = self.chat_agent
        old_error = self.llm_error

        if self.chat_agent is not None:
            try:
                self.chat_agent.set_main_profile(
                    model=profile.main.model,
                    reasoning_effort=profile.main.reasoning_effort,
                )
                self.chat_agent.set_subagent_profile(
                    model=profile.subagent.model,
                    reasoning_effort=profile.subagent.reasoning_effort,
                )
            except Exception:
                with suppress(Exception):
                    self.chat_agent.set_main_profile(
                        model=old_profile.main.model,
                        reasoning_effort=old_profile.main.reasoning_effort,
                    )
                with suppress(Exception):
                    self.chat_agent.set_subagent_profile(
                        model=old_profile.subagent.model,
                        reasoning_effort=old_profile.subagent.reasoning_effort,
                    )
                self.llm_profile = old_profile
                self.chat_agent = old_agent
                self.llm_error = old_error
                raise
            else:
                self.llm_profile = profile
                self.llm_error = None
            return

        new_agent = self._build_chat_agent(profile=profile)
        self.llm_profile = profile
        self.chat_agent = new_agent
        self.llm_error = None

    @property
    def subagent_api_key(self) -> str | None:
        return self.chat_agent.subagent_api_key if self.chat_agent is not None else None

    @property
    def subagent_supported_efforts(self) -> tuple[str, ...]:
        return self.chat_agent.subagent_supported_efforts if self.chat_agent is not None else ()

    @property
    def subagent_reasoning_effort(self) -> str:
        return self.llm_profile.subagent.reasoning_effort

    async def close(self) -> None:
        """Release session-owned runtime resources."""
        if self.chat_agent is not None:
            await self.chat_agent.aclose()
        await self.registry.disconnect_all_async()
