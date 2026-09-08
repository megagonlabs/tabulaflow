"""Non-visual runtime for one interactive app session."""

from __future__ import annotations

import logging
import os
import shutil
import threading
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.config import LLMPreset, model_supports_apply_patch
from tabulaflow.app.runtime_paths import RuntimePaths

if TYPE_CHECKING:
    from tabulaflow.agents.chat import ChatEvent, ChatInput, ChatSession
    from tabulaflow.agents.llm import ServiceTier
    from tabulaflow.agents.trace import Usage
    from tabulaflow.app.turn import TurnOutput
    from tabulaflow.data.sql import SQLConnector
    from tabulaflow.data.catalog import DataSourceDefinition
    from tabulaflow.output.specs import OutputSpec

WORKSPACE_ALIAS = "workspace"
logger = logging.getLogger(__name__)


async def _create_workspace_connector(workspace_db_path: Path) -> SQLConnector:
    """Create the session's writable DuckDB connector."""
    from tabulaflow.data.sql import SQLConnector
    from tabulaflow.data.config import SQLConnectorConfig

    workspace_db_path.parent.mkdir(parents=True, exist_ok=True)
    abspath = os.path.abspath(workspace_db_path)
    return await SQLConnector.from_url_async(
        global_id=f"cli+{WORKSPACE_ALIAS}",
        url=f"duckdb:///{abspath}",
        display_name=WORKSPACE_ALIAS,
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
        duckdb_init_sql=["SET TimeZone='UTC'"],
    )


class AppSession:
    """Owns data sources and agent state for one interactive app session."""

    @classmethod
    async def create(
        cls,
        *,
        llm_preset: LLMPreset | None,
        runtime_paths: RuntimePaths,
        project_dir: Path,
        service_tier: ServiceTier = "default",
        data_source_definitions: Sequence[DataSourceDefinition] | None = None,
    ) -> AppSession:
        """Create a ready session with its workspace and optional sample data."""
        import asyncio

        await asyncio.to_thread(_warm_connector_imports)
        runtime_paths.scratch_dir.mkdir(parents=True, exist_ok=True)
        workspace: SQLConnector | None = None
        try:
            workspace = await _create_workspace_connector(runtime_paths.workspace_db_path)
            session = cls(
                llm_preset=llm_preset,
                runtime_paths=runtime_paths,
                workspace=workspace,
                service_tier=service_tier,
                project_dir=project_dir,
                data_source_definitions=data_source_definitions,
            )
        except BaseException:
            if workspace is not None:
                try:
                    await workspace.close_async()
                except Exception:
                    logger.debug("workspace cleanup failed during session creation", exc_info=True)
            shutil.rmtree(runtime_paths.scratch_dir, ignore_errors=True)
            raise

        from tabulaflow.app.sample_data import autoconnect_sample

        try:
            await autoconnect_sample(session)
        except Exception:
            logger.debug("sample data auto-connect failed", exc_info=True)
        return session

    def __init__(
        self,
        llm_preset: LLMPreset | None,
        runtime_paths: RuntimePaths,
        workspace: SQLConnector | None,
        service_tier: ServiceTier = "default",
        project_dir: Path | None = None,
        data_source_definitions: Sequence[DataSourceDefinition] | None = None,
    ) -> None:
        from tabulaflow.data.registry import DataConnectorRegistry
        from tabulaflow.data.catalog import DEFAULT_DATA_SOURCE_DEFINITIONS

        self._runtime_paths = runtime_paths
        self._selected_preset = llm_preset
        self._service_tier = service_tier
        self._workspace = workspace
        self.project_dir = project_dir
        self.data_source_definitions = tuple(
            DEFAULT_DATA_SOURCE_DEFINITIONS if data_source_definitions is None else data_source_definitions
        )
        self.registry: DataConnectorRegistry = DataConnectorRegistry()
        if workspace is not None:
            self.registry.register(WORKSPACE_ALIAS, workspace)
        self._chat_session: ChatSession | None = None
        self._activation_lock = threading.Lock()
        self._closed = False

    @property
    def data_dir(self) -> Path:
        """Directory for session-local data caches."""
        return self._runtime_paths.data_dir

    @property
    def selected_preset(self) -> LLMPreset | None:
        """Return the LLM preset selected for this session."""
        return self._selected_preset

    @property
    def active_chat_session(self) -> ChatSession | None:
        """Return the chat session active for the selected preset, if initialized."""
        if self._selected_preset is None or not self._chat_session_matches_preset(self._selected_preset):
            return None
        return self._chat_session

    @property
    def llm_available(self) -> bool:
        """Whether the selected LLM preset is ready to run turns."""
        return self.active_chat_session is not None

    def _chat_session_matches_preset(self, preset: LLMPreset) -> bool:
        agent = self._chat_session
        return (
            agent is not None
            and agent.model == preset.main.model
            and agent.reasoning == preset.main.reasoning
            and agent.subagent_model == preset.subagent.model
            and agent.subagent_reasoning == preset.subagent.reasoning
            and agent.use_apply_patch == model_supports_apply_patch(preset.main.model)
        )

    def _build_chat_session(
        self,
        *,
        preset: LLMPreset,
    ) -> ChatSession:
        from tabulaflow.agents.chat import ChatSession

        return ChatSession(
            registry=self.registry,
            model=preset.main.model,
            reasoning=preset.main.reasoning,
            service_tier=self._service_tier,
            workspace=self._workspace,
            trajectory_log_dir=self._runtime_paths.trajectories_dir,
            subagent_model=preset.subagent.model,
            subagent_reasoning=preset.subagent.reasoning,
            project_dir=self.project_dir,
            scratch_dir=self._runtime_paths.scratch_dir,
            data_dir=self.data_dir,
            use_apply_patch=model_supports_apply_patch(preset.main.model),
            data_source_definitions=self.data_source_definitions,
        )

    def select_llm_preset(self, preset: LLMPreset | None) -> None:
        """Select the only LLM preset allowed to answer new turns."""
        self._selected_preset = preset

    def activate_llm_preset(self, preset: LLMPreset | None) -> tuple[str | None, str | None]:
        """Activate ``preset`` without changing the session's current selection."""
        if preset is None:
            return None, None
        with self._activation_lock:
            if self._chat_session is None:
                agent = self._build_chat_session(preset=preset)
                keys = agent.resolve_api_keys()
                self._chat_session = agent
                return keys
            if not self._chat_session_matches_preset(preset):
                return self._chat_session.activate_llm_profile(
                    model=preset.main.model,
                    reasoning=preset.main.reasoning,
                    subagent_model=preset.subagent.model,
                    subagent_reasoning=preset.subagent.reasoning,
                    use_apply_patch=model_supports_apply_patch(preset.main.model),
                )
            return self._chat_session.resolve_api_keys()

    def note_event(self, description: str) -> None:
        """Append an app event to the chat session when LLM support is available."""
        if self._chat_session is not None:
            self._chat_session.note_event(description)

    def reset_conversation(self) -> None:
        """Reset LLM conversation state while preserving data sources and workspace state."""
        if self._chat_session is not None:
            self._chat_session.reset_conversation()

    def run_stream(self, question: "ChatInput") -> AsyncIterator[ChatEvent]:
        """Run one agent turn with the active LLM preset."""
        chat_session = self.active_chat_session
        if chat_session is None:
            raise RuntimeError("LLM is not available")
        return chat_session.run_stream(question)

    @property
    def last_usage(self) -> Usage | None:
        """Return usage from the most recent agent turn, if available."""
        return self._chat_session.last_usage if self._chat_session is not None else None

    def turn_output(self, output: OutputSpec) -> TurnOutput:
        """Bind an output specification to this session's result store."""
        if self._chat_session is None:
            raise RuntimeError("Chat session is not initialized")
        from tabulaflow.app.turn import TurnOutput

        return TurnOutput(output, self._chat_session.output_store)

    async def disconnect_source(self, alias: str) -> bool:
        """Disconnect ``alias`` and notify the active conversation."""
        if not await self.registry.close_async(alias):
            return False
        self.note_event(f"the user disconnected the data source `{alias}`; it is no longer available.")
        return True

    async def close(self) -> None:
        """Release session-owned runtime resources."""
        if self._closed:
            return
        self._closed = True
        try:
            if self._chat_session is not None:
                await self._chat_session.aclose()
        finally:
            try:
                await self.registry.close_all_async()
            finally:
                shutil.rmtree(self._runtime_paths.scratch_dir, ignore_errors=True)
                shutil.rmtree(self.data_dir, ignore_errors=True)


def _warm_connector_imports() -> None:
    """Load the connector stack away from the UI event loop."""
    import tabulaflow.data.sql  # noqa: F401
