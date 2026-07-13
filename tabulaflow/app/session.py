"""Per-session app state — DB registry, optional chat agent, and source aliases."""

from __future__ import annotations

from contextlib import suppress
import os
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.config import LLMPreset

if TYPE_CHECKING:
    from tabulaflow.chat import ChatAgent
    from tabulaflow.core.db_connector.base import NL2QDBConnector
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

WORKSPACE_ALIAS = "workspace"


def format_llm_unavailable_message(_error: str | None) -> str:
    """Return the full chat-surface message for unavailable LLM actions."""
    return "Select a configured preset in /config. /connect and data browsing still work."


def compact_model_name(model: str) -> str:
    """Return a compact display name for an LLM model identifier."""
    _, sep, name = model.partition(":")
    if not sep:
        name = model
    name = name.rsplit("/", 1)[-1]
    tokens = name.replace("_", "-").split("-")
    if len(tokens) > 1 and tokens[-1].isdigit() and len(tokens[-1]) == 8:
        tokens = tokens[:-1]
    if len(tokens) >= 2 and tokens[-1].isdigit() and tokens[-2].isdigit():
        tokens = [*tokens[:-2], f"{tokens[-2]}.{tokens[-1]}"]
    if tokens and tokens[0].lower() == "claude":
        tokens = tokens[1:]
    parts: list[str] = []
    for tok in tokens:
        if tok.lower() == "gpt":
            parts.append(tok.upper())
        elif tok[:1].isalpha():
            parts.append(tok.capitalize())
        else:
            parts.append(tok)
    return " ".join(parts)


def compact_model_label(model: str, reasoning_effort: str | None = None) -> str:
    """Return a compact model label with optional reasoning effort."""
    label = compact_model_name(model)
    return f"{label} {reasoning_effort}" if reasoning_effort else label


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
        llm_preset: LLMPreset | None,
        session_id: str,
        trajectories_dir: Path,
        data_dir: Path,
        workspace: SQLConnector | None,
        service_tier: str | None = "priority",
        project_dir: Path | None = None,
        scratch_dir: Path | None = None,
    ) -> None:
        from tabulaflow.core.db_connector.db_registry import DBRegistry

        self.session_id = session_id
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
        self.chat_agent: ChatAgent | None = None
        self._retired_chat_agents: list[ChatAgent] = []
        self.llm_error: str | None = None
        self.last_result: object | None = None
        # Maps a "what's this connection's source" key (frozenset of file
        # paths, normalized URL, etc.) to the alias under which it is
        # registered.  Used by ``/connect`` to detect duplicate sources
        # being registered under different aliases.
        self._sources: dict[object, str] = {}

    @property
    def llm_available(self) -> bool:
        """Whether the selected LLM preset has a constructed live chat agent."""
        return self.chat_agent is not None

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

    def ensure_chat_agent(self) -> ChatAgent:
        """Return the live chat agent, building it lazily for the selected preset."""
        if self.chat_agent is not None:
            return self.chat_agent
        if self.llm_preset is None:
            raise RuntimeError("No LLM preset is selected.")
        try:
            self.chat_agent = self._build_chat_agent(preset=self.llm_preset)
        except Exception as e:
            self.chat_agent = None
            self.llm_error = str(e)
            raise
        else:
            self.llm_error = None
            return self.chat_agent

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
        return self._require_llm_preset().main.model

    @property
    def api_key(self) -> str | None:
        return self.chat_agent.api_key if self.chat_agent is not None else None

    @property
    def supported_efforts(self) -> tuple[str, ...]:
        return self.chat_agent.supported_efforts if self.chat_agent is not None else ()

    @property
    def reasoning_effort(self) -> str:
        return self._require_llm_preset().main.reasoning_effort

    @property
    def subagent_model(self) -> str:
        return self._require_llm_preset().subagent.model

    def set_llm_preset(self, preset: LLMPreset) -> None:
        """Select an LLM preset without constructing provider clients."""
        if (
            self.llm_preset is not None
            and preset.main == self.llm_preset.main
            and preset.subagent == self.llm_preset.subagent
        ):
            self.llm_error = None
            return
        if self.chat_agent is not None:
            self._retired_chat_agents.append(self.chat_agent)
        self.llm_preset = preset
        self.chat_agent = None
        self.llm_error = None

    @property
    def subagent_api_key(self) -> str | None:
        return self.chat_agent.subagent_api_key if self.chat_agent is not None else None

    @property
    def subagent_supported_efforts(self) -> tuple[str, ...]:
        return self.chat_agent.subagent_supported_efforts if self.chat_agent is not None else ()

    @property
    def subagent_reasoning_effort(self) -> str:
        return self._require_llm_preset().subagent.reasoning_effort

    def _require_llm_preset(self) -> LLMPreset:
        if self.llm_preset is None:
            raise RuntimeError("No LLM preset is selected.")
        return self.llm_preset

    async def close(self) -> None:
        """Release session-owned runtime resources."""
        if self.chat_agent is not None:
            await self.chat_agent.aclose()
        for agent in self._retired_chat_agents:
            with suppress(Exception):
                await agent.aclose()
        await self.registry.disconnect_all_async()
