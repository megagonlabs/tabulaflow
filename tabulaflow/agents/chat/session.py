"""Reusable stateful chat session."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from datetime import date
from importlib.resources import files
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai.settings import ModelSettings
from pydantic_ai.messages import BinaryContent
from pydantic_ai.usage import RunUsage

from tabulaflow.agents.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    MessageStore,
    MessageStoreCapability,
    make_snippet,
)
from tabulaflow.agents.tools.browser.tool import (
    BROWSER_TOOL_NAMES,
    SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
    snapshot_snippet,
)
from tabulaflow.output.formatting import format_connector_summary
from tabulaflow.agents.llm import ReasoningLevel, ServiceTier, make_agent, make_model_settings, model_display_name
from tabulaflow.agents.chat.events import (
    ChatEvent,
    ChatResult,
    CompactionFinished,
    CompactionStarted,
    TurnFinished,
    ToolProgress,
    UsageUpdated,
)
from tabulaflow.agents.chat.input import ChatInput, describe_chat_input
from tabulaflow.agents.chat.compaction import (
    CompactionConfig,
    HOST_EVENT_METADATA_KEY,
    checkpoint_prompt,
    compact_history,
    effective_trigger_tokens,
    estimate_context_tokens,
)
from tabulaflow.agents.chat.tools import _ChatTools
from tabulaflow.agents.chat.turn import (
    _TextStreamRouter,
    _build_chat_result,
    _declared_bundle,
    _emit_stream_event,
    _patch_incomplete_messages,
    _strip_answer_prefix,
)

if TYPE_CHECKING:
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage, ToolReturnPart

    from tabulaflow.data.registry import DataConnectorRegistry
    from tabulaflow.data.sql import SQLConnector
    from tabulaflow.agents.trace import Usage
    from tabulaflow.agents.tools.protocols import ToolProgressUpdate
    from tabulaflow.agents.tools.shell.tool import ExecuteBashTool
    from tabulaflow.output.store import OutputStore

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = files("tabulaflow.agents.chat").joinpath("system_prompt.md").read_text(encoding="utf-8").strip()


DEFAULT_SUBAGENT_MODEL: Final = "openai-responses:gpt-5.4-mini"
DEFAULT_SUBAGENT_REASONING: Final[ReasoningLevel] = "medium"
# Non-streaming subagent requests occasionally stall server-side for many
# minutes (a fan-out visibly stuck at "28/30" rows), while a re-sent identical
# request completes in seconds. The provider SDK retries timed-out requests
# automatically, so this cap turns a stalled row into a quick re-roll.
SUBAGENT_REQUEST_TIMEOUT: Final = 120.0
# The interactive agent streams, so its read timeout bounds the *silence
# between chunks* (pings/deltas flow every few seconds when healthy), not turn
# duration. Higher than the subagent cap because a mid-stream trip is not
# retried by the SDK — it fails the turn — and the worst legitimate silence
# (cold prefill of a very long history) can exceed a minute.
MAIN_REQUEST_TIMEOUT: Final = 180.0


def _shorten_stored_input(value: str | list[str | BinaryContent], message_id: str) -> str | list[str | BinaryContent]:
    if isinstance(value, str):
        return make_snippet(message_id, value) if len(value) > MESSAGE_THRESHOLD_CHARS else value

    shortened: list[str | BinaryContent] = []
    for item in value:
        if isinstance(item, str) and len(item) > MESSAGE_THRESHOLD_CHARS:
            shortened.append(make_snippet(message_id, item))
        else:
            shortened.append(item)
    return shortened


class ChatSession:
    """Stateful runtime for one interactive database conversation.

    A session owns conversation history, tools, outputs, and model state and runs
    one turn at a time. Call :meth:`aclose` when the session is no longer needed.

    Args:
        registry: Data sources available to the conversation.
        model: Provider-qualified model identifier for the interactive agent.
        reasoning: Provider-neutral reasoning level for the main model.
        service_tier: Optional provider service tier.
        subagent_model: Model used by fan-out and extraction helpers.
        subagent_reasoning: Reasoning level for helper models.
        use_apply_patch: Use ``apply_patch`` instead of ``edit_file`` when filesystem tools are available.
        extra_instructions: Instructions appended to the fixed baseline prompt.
        trajectory_log_dir: Optional directory for conversation trajectories.
        workspace: Writable SQL scratch database for derived data and message spill.
        project_dir: Host project directory; enables filesystem tools.
        scratch_dir: Transient directory exposed to shell workflows.
        data_dir: Directory where connected file sources are materialized.
        compaction: Automatic context-compaction policy, or ``None`` to disable it.
    """

    def __init__(
        self,
        registry: DataConnectorRegistry,
        *,
        model: str,
        reasoning: ReasoningLevel,
        service_tier: ServiceTier | None = None,
        subagent_model: str = DEFAULT_SUBAGENT_MODEL,
        subagent_reasoning: ReasoningLevel = DEFAULT_SUBAGENT_REASONING,
        use_apply_patch: bool = False,
        extra_instructions: str | None = None,
        trajectory_log_dir: Path | None = None,
        workspace: SQLConnector | None = None,
        project_dir: Path | None = None,
        scratch_dir: Path | None = None,
        data_dir: Path | None = None,
        compaction: CompactionConfig | None = CompactionConfig(),
    ) -> None:
        self._registry = registry
        self._model = model
        self._reasoning = reasoning
        self._service_tier = service_tier
        self._subagent_model = subagent_model
        self._subagent_reasoning = subagent_reasoning
        self._use_apply_patch = use_apply_patch
        self._extra_instructions = extra_instructions
        self._trajectory_log_dir = trajectory_log_dir
        self._workspace = workspace
        self._project_dir = project_dir
        self._scratch_dir = scratch_dir
        self._data_dir = data_dir
        self._compaction = compaction
        self._last_usage: Usage | None = None
        self._context_messages: list[ModelMessage] = []
        self._transcript_messages: list[ModelMessage] = []
        self._system_prompt = _SYSTEM_PROMPT
        self._pydantic_ai_agent: Agent[object, str] | None = None
        self._running = False
        self._active_emit: Callable[[ChatEvent], None] | None = None

        from tabulaflow.agents.tools.protocols import ProgressReportingTool
        from tabulaflow.output.store import OutputStore

        self._output_store: OutputStore = OutputStore(
            spill_dir=scratch_dir / "result_dataframes" if scratch_dir is not None else None,
            registry=registry,
        )
        self._message_store = MessageStore(workspace)
        self._main_scope = self._message_store.scoped("main")
        subagent_dir = trajectory_log_dir / "subagents" if trajectory_log_dir is not None else None
        self._tools = self._build_tools(subagent_dir)
        for tool in self._tools:
            if isinstance(tool, ProgressReportingTool):
                tool.on_progress = self._emit_progress
        if workspace is not None:
            self._tools.add_canonical_name.attach_connector(workspace)
        self._system_prompt = self._compose_system_prompt()
        self._seed_conversation_context()
        self._pydantic_ai_agent = self._make_agent(model)

    @property
    def model(self) -> str:
        """Active interactive model; change it through :meth:`activate_llm_profile`."""
        return self._model

    @property
    def reasoning(self) -> ReasoningLevel:
        """Active reasoning level for the interactive model."""
        return self._reasoning

    @property
    def subagent_model(self) -> str:
        """Active model for fan-out and extraction helpers."""
        return self._subagent_model

    @property
    def subagent_reasoning(self) -> ReasoningLevel:
        """Active reasoning level for helper models."""
        return self._subagent_reasoning

    @property
    def use_apply_patch(self) -> bool:
        """Whether the active profile uses ``apply_patch`` instead of ``edit_file``."""
        return self._use_apply_patch

    @property
    def last_usage(self) -> Usage | None:
        """Latest turn usage, including partial usage after interruption, or ``None``."""
        return self._last_usage

    def _compose_system_prompt(self) -> str:
        """Assemble the agent's instructions: the baseline ``_SYSTEM_PROMPT``, then any
        host ``extra_instructions``, then the ``## Session`` tail. The ordering keeps
        the large static prefix first so it prompt-caches, and the session facts last."""
        parts = [_SYSTEM_PROMPT]
        if self._extra_instructions:
            parts.append(self._extra_instructions.strip())
        session_lines = []
        if self._project_dir is not None:
            session_lines.append(f"- Project directory: {self._project_dir}")
        if self._scratch_dir is not None:
            session_lines.append(f"- Scratch directory: {self._scratch_dir}")
        session_lines.append(f"- Platform: {sys.platform}")
        session_lines.append(f"- Today's date: {date.today().isoformat()}")
        parts.append("## Session\n\n" + "\n".join(session_lines))
        return "\n\n".join(parts)

    def _build_tools(self, subagent_dir: Path | None) -> _ChatTools:
        """Construct the agent's toolset, wiring in the shared output store and
        message store. ``subagent_dir`` (if set) is where subagent trajectories land."""
        from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter
        from tabulaflow.agents.summarization import DBSummarizer
        from tabulaflow.agents.tools.add_canonical_name import AddCanonicalNameTool
        from tabulaflow.agents.tools.filesystem.patch import ApplyPatchTool
        from tabulaflow.agents.tools.connect_data_source import ConnectDataSourceTool
        from tabulaflow.agents.tools.create_parameterized_source import CreateParameterizedArtifactSourceTool
        from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
        from tabulaflow.agents.tools.filesystem.edit import EditFileTool
        from tabulaflow.agents.tools.filesystem.view import ViewTool
        from tabulaflow.agents.tools.registry.get_column_json_schema import RegistryGetColumnJsonSchemaTool
        from tabulaflow.agents.tools.registry.get_db_document import RegistryGetDBDocumentTool
        from tabulaflow.agents.tools.registry.get_table_schema import RegistryGetTableSchemaTool
        from tabulaflow.agents.tools.registry.run_query import RegistryRunQueryTool
        from tabulaflow.agents.tools.registry.write_result_table import WriteResultTableTool
        from tabulaflow.agents.tools.render_chart import RenderChartTool
        from tabulaflow.agents.tools.render_graph import RenderGraphTool
        from tabulaflow.agents.tools.render_map import RenderMapTool
        from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
        from tabulaflow.agents.tools.show_artifacts import ShowArtifactsTool
        from tabulaflow.agents.tools.browser.tool import WebBrowserTool

        # The fan-out tools operate on the workspace only: sub-tasks are laid out
        # as workspace tables and results written back there (user data reaches
        # them via write_result_table). Without a workspace they are disabled.
        run_subagent_for_each_row = None
        extract_rows_from_documents = None
        if self._workspace is not None:
            run_subagent_for_each_row = RunSubagentForEachRowTool(
                self._workspace,
                registry=self._registry,
                message_store=self._message_store,
                subagent_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                store_metadata=True,
                trajectory_log_dir=subagent_dir,
            )
            extract_rows_from_documents = ExtractRowsFromDocumentsTool(
                self._workspace,
                subagent_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                trajectory_log_dir=subagent_dir,
            )

        return _ChatTools(
            run_query=RegistryRunQueryTool(
                self._registry,
                output_store=self._output_store,
                enable_refresh=True,
                enable_media=True,
            ),
            create_parameterized_source=CreateParameterizedArtifactSourceTool(
                self._registry, output_store=self._output_store
            ),
            get_db_document=RegistryGetDBDocumentTool(
                self._registry,
                db_summarizer_cls=DBSummarizer,
                db_summarizer_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                enable_refresh=True,
            ),
            get_table_schema=RegistryGetTableSchemaTool(self._registry, SQLDDLSchemaFormatter(), enable_refresh=True),
            get_column_json_schema=RegistryGetColumnJsonSchemaTool(self._registry),
            write_result_table=WriteResultTableTool(self._registry, self._output_store),
            run_subagent_for_each_row=run_subagent_for_each_row,
            extract_rows_from_documents=extract_rows_from_documents,
            connect_data_source=(
                ConnectDataSourceTool(self._registry, self._data_dir) if self._data_dir is not None else None
            ),
            bash=self._build_bash_tool(),
            view=(
                ViewTool(
                    str(self._project_dir),
                    allowed_roots=None,
                )
                if self._project_dir is not None
                else None
            ),
            edit_file=(
                EditFileTool(
                    str(self._project_dir),
                    allowed_roots=None,
                )
                if self._project_dir is not None
                else None
            ),
            apply_patch=(
                ApplyPatchTool(
                    str(self._project_dir),
                    allowed_roots=None,
                )
                if self._project_dir is not None
                else None
            ),
            add_canonical_name=AddCanonicalNameTool(
                subagent_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                trajectory_log_dir=subagent_dir,
            ),
            render_chart=RenderChartTool(output_store=self._output_store),
            render_graph=RenderGraphTool(output_store=self._output_store),
            render_map=RenderMapTool(output_store=self._output_store),
            show_artifacts=ShowArtifactsTool(output_store=self._output_store),
            web_browser=WebBrowserTool(),
        )

    def _build_bash_tool(self) -> ExecuteBashTool | None:
        """Build the shell tool, or ``None`` when the host dirs aren't available.

        Runs commands in the user's project dir, exposes the session scratch dir as
        ``$SCRATCH``, and guards against catastrophic commands via the denylist."""
        if self._project_dir is None or self._scratch_dir is None:
            return None
        import os

        if os.name != "posix":
            # The shell tool is POSIX-only. Omit it so the rest of the app
            # still runs on Windows; the agent just loses shell-based gather/transform.
            logger.warning("execute_bash is unavailable on this platform; the agent runs without a shell tool")
            return None

        # The shell tool runs with cwd=project_dir, while in-process run_query/DuckDB
        # resolve relative paths against the live process cwd. The "relative = project
        # dir" design requires these to be equal — assert it loudly rather than silently
        # reading/writing the wrong files if something ever changed cwd.
        if os.path.realpath(os.getcwd()) != os.path.realpath(self._project_dir):
            raise RuntimeError(
                f"process cwd ({os.getcwd()!r}) != project_dir ({str(self._project_dir)!r}); "
                "relative-path resolution would diverge between the shell tool and run_query."
            )

        from tabulaflow.agents.tools.shell.guard import dangerous_command_reason
        from tabulaflow.agents.tools.shell.tool import ExecuteBashTool

        return ExecuteBashTool(
            working_dir=str(self._project_dir),
            job_dir=self._scratch_dir / "bash-jobs",
            env_overrides={"SCRATCH": str(self._scratch_dir)},
            command_filter=dangerous_command_reason,
        )

    @property
    def output_store(self) -> OutputStore:
        """The live output store — results the agent's answers reference."""
        return self._output_store

    @staticmethod
    def _unwrap_model(model: object) -> object:
        """Return the provider model beneath tabulaflow/pydantic-ai wrappers."""
        from pydantic_ai.models.wrapper import WrapperModel

        while isinstance(model, WrapperModel):
            model = model.wrapped
        return model

    def _unwrapped_model(self) -> Any | None:
        """The live provider model beneath tabulaflow's wrappers, or None."""
        if self._pydantic_ai_agent is None:
            return None
        return self._unwrap_model(self._pydantic_ai_agent.model)

    def _subagent_provider_model(self, model: str) -> object:
        """Construct ``model`` as a subagent provider model for introspection."""
        return self._unwrap_model(make_agent(model).model)

    @staticmethod
    def _api_key_from_model(model: object | None) -> str | None:
        key = getattr(getattr(model, "client", None), "api_key", None)
        return key if isinstance(key, str) and key else None

    def resolve_api_keys(self) -> tuple[str | None, str | None]:
        """Resolve API keys for the configured main and subagent providers.

        The main key comes from the live client. The subagent provider is
        constructed locally because subagents have no persistent client.
        Provider construction errors propagate so callers can treat the whole
        profile as one readiness boundary. No network request is made. Returned
        values are raw credentials for trusted host integration and must not be logged.
        """
        return (
            self._api_key_from_model(self._unwrapped_model()),
            self._api_key_from_model(self._subagent_provider_model(self.subagent_model)),
        )

    def _thinking_settings(self) -> ModelSettings:
        """Return the shared provider-specific settings for the interactive model."""
        return make_model_settings(
            model=self.model,
            reasoning=self.reasoning,
            timeout=MAIN_REQUEST_TIMEOUT,
        )

    def _subagent_model_settings(
        self,
        *,
        model: str | None = None,
        reasoning: ReasoningLevel | None = None,
    ) -> ModelSettings:
        """Model settings for subagent-backed tools.

        Use provider-neutral thinking settings by default. OpenAI Responses gets
        detailed reasoning summaries through the shared reasoning settings helper.
        """
        return make_model_settings(
            model=model or self.subagent_model,
            reasoning=self.subagent_reasoning if reasoning is None else reasoning,
            service_tier=self._service_tier,
            timeout=SUBAGENT_REQUEST_TIMEOUT,
        )

    def _emit_progress(self, update: ToolProgressUpdate) -> None:
        """Forward a tool's progress tick to the active turn's event stream.

        Wired once into every ``ProgressReportingTool`` at construction; a tick
        arriving between turns is dropped."""
        if self._active_emit is not None:
            self._active_emit(
                ToolProgress(
                    completed=update.completed,
                    total=update.total,
                    unit=update.unit,
                    stage=update.stage,
                    tool_call_id=update.tool_call_id,
                )
            )

    def _apply_subagent_profile(self, *, model: str, reasoning: ReasoningLevel) -> None:
        """Update the tools whose internal helper LLM follows the app subagent profile."""
        from tabulaflow.agents.tools.protocols import LLMProfileTool

        model_settings = self._subagent_model_settings(model=model, reasoning=reasoning)
        for tool in self._tools:
            if isinstance(tool, LLMProfileTool):
                tool.apply_llm_profile(llm=model, model_settings=model_settings)

    def activate_llm_profile(
        self,
        *,
        model: str,
        reasoning: ReasoningLevel,
        subagent_model: str,
        subagent_reasoning: ReasoningLevel,
        use_apply_patch: bool,
    ) -> tuple[str | None, str | None]:
        """Atomically activate main and subagent LLM profiles.

        Conversation, query, tool, and message-store state remain attached to
        this ``ChatSession``. Provider runtimes are prepared before the live
        profile is changed, so a construction failure leaves the old profile
        usable. A main-model change is recorded in the conversation history
        (see ``_note_profile_change``). Returns the API keys resolved during
        preparation.

        Args:
            model: New interactive model identifier.
            reasoning: New interactive reasoning level.
            subagent_model: New helper model identifier.
            subagent_reasoning: New helper reasoning level.
            use_apply_patch: Whether to use ``apply_patch`` instead of ``edit_file``.

        Returns:
            Raw main and subagent API keys, when their resolved clients use keys.

        Raises:
            RuntimeError: If a turn is active.
        """
        if self._running:
            raise RuntimeError("cannot change the LLM profile during an active turn")
        unchanged = (
            self.model == model
            and self.reasoning == reasoning
            and self.subagent_model == subagent_model
            and self.subagent_reasoning == subagent_reasoning
            and self.use_apply_patch == use_apply_patch
        )

        runtime_agent = self._pydantic_ai_agent
        if self.model != model or self.use_apply_patch != use_apply_patch:
            runtime_agent = self._make_agent(model, use_apply_patch=use_apply_patch)
        subagent_provider_model = self._subagent_provider_model(subagent_model)
        keys = (
            self._api_key_from_model(self._unwrap_model(runtime_agent.model) if runtime_agent is not None else None),
            self._api_key_from_model(subagent_provider_model),
        )
        if unchanged:
            return keys

        previous_model = self.model
        previous_use_apply_patch = self.use_apply_patch
        previous_subagent_model = self.subagent_model
        previous_subagent_effort = self.subagent_reasoning
        try:
            self._apply_subagent_profile(
                model=subagent_model,
                reasoning=subagent_reasoning,
            )
        except Exception:
            self._apply_subagent_profile(
                model=previous_subagent_model,
                reasoning=previous_subagent_effort,
            )
            raise
        self._model = model
        self._reasoning = reasoning
        self._subagent_model = subagent_model
        self._subagent_reasoning = subagent_reasoning
        self._use_apply_patch = use_apply_patch
        self._pydantic_ai_agent = runtime_agent
        if model != previous_model or use_apply_patch != previous_use_apply_patch:
            self._note_profile_change(
                previous_model,
                model,
                previous_use_apply_patch=previous_use_apply_patch,
                use_apply_patch=use_apply_patch,
            )
        return keys

    def note_event(self, description: str) -> None:
        """Make the agent aware of a host/app event (typically a user action — e.g.
        connecting a data source, uploading a file) by appending it to the
        conversation. The caller supplies ``description`` in its own domain terms;
        the agent owns how it enters the conversation: a system-tagged turn in the
        message history.

        Events go in the message history, not the system instructions, on purpose:
        the instructions stay static so the model's large prompt prefix is fully
        prompt-cached, and each event is a pure append to the history tail — itself
        cache-friendly. The message also gives the agent temporal awareness (it
        knows the event *just* happened)."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        message = ModelRequest(
            parts=[UserPromptPart(content=f"[system: {description}]")],
            metadata={HOST_EVENT_METADATA_KEY: True},
        )
        self._context_messages.append(message)
        self._transcript_messages.append(message)

    def _note_profile_change(
        self,
        previous_model: str,
        model: str,
        *,
        previous_use_apply_patch: bool,
        use_apply_patch: bool,
    ) -> None:
        """Record model and tool-capability changes in conversation history."""
        parts = []
        if model != previous_model:
            parts.append(
                "the model powering this conversation changed from "
                f"{model_display_name(previous_model)} to {model_display_name(model)}"
            )
        if self._tools.apply_patch is not None and use_apply_patch != previous_use_apply_patch:
            if use_apply_patch:
                parts.append("apply_patch is now available and replaces edit_file")
            else:
                parts.append("edit_file is now available and replaces apply_patch")
        if parts:
            self.note_event("; ".join(parts) + ".")

    def _note_initial_registry(self) -> None:
        aliases = self._registry.list_aliases()
        if not aliases:
            return

        entries = []
        for alias in aliases:
            try:
                connector = self._registry.get(alias)
            except ValueError:
                continue
            entries.append(f"`{alias}` ({format_connector_summary(connector)})")

        if entries:
            self.note_event("the following data sources are already registered: " + ", ".join(entries) + ".")

    def _seed_conversation_context(self) -> None:
        self.note_event(f"the model powering this conversation is {model_display_name(self.model)}.")
        self._note_initial_registry()

    def reset_conversation(self) -> None:
        """Start a fresh conversation while preserving the session environment."""
        if self._running:
            raise RuntimeError("cannot reset conversation while a turn is running")
        self._context_messages.clear()
        self._transcript_messages.clear()
        self._last_usage = None
        self._seed_conversation_context()

    async def aclose(self) -> None:
        """Release session-scoped resources, including active shell jobs."""
        if self._tools.bash is not None:
            await self._tools.bash.close()

    def _make_agent(self, model: str, *, use_apply_patch: bool | None = None) -> Agent[object, str]:
        """Construct the model-specific runtime around the session's live tools."""
        from tabulaflow.agents.tools.run_subagent_for_each_row import ReleaseBrowserBeforeFanout

        if use_apply_patch is None:
            use_apply_patch = self.use_apply_patch
        tools: list[Any] = []
        for tool in self._tools:
            if tool is self._tools.apply_patch and not use_apply_patch:
                continue
            if tool is self._tools.edit_file and use_apply_patch:
                continue
            if tool is self._tools.web_browser:
                tools.extend(tool.as_pydantic_ai_tools())
            else:
                tools.append(tool.as_pydantic_ai_tool())
        return make_agent(
            model,
            tools=tools,
            capabilities=[
                self._tools.web_browser.lifecycle_capability(),
                # Suspend the root agent's browser around any fan-out it triggers,
                # so it holds no page permits while awaiting subagent rows that
                # need them (same deadlock-avoidance as for non-leaf subagents).
                ReleaseBrowserBeforeFanout(browser_tool=self._tools.web_browser),
                MessageStoreCapability(
                    store=self._main_scope,
                    tool_allowlist=BROWSER_TOOL_NAMES,
                    snippet_fn=snapshot_snippet,
                    threshold_chars=SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
                ),
            ],
            instructions=self._system_prompt,
            # Thinking is deliberately absent: effort is passed per request in
            # ``run_stream`` so effort changes need no agent rebuild.
            model_settings=make_model_settings(model=model, service_tier=self._service_tier),
        )

    async def run_stream(self, question: ChatInput) -> AsyncIterator[ChatEvent]:
        """Run the agent on a user question, yielding progress as ``ChatEvent``s.

        The stream ends with exactly one ``TurnFinished`` (carrying the ``ChatResult``)
        on normal completion. Failures propagate as exceptions. To interrupt, cancel
        the task iterating this generator: it raises ``CancelledError`` and the
        agent's message history / ``last_usage`` are left reflecting the partial run.

        The agent loop runs as a background task (``_run_to_queue``) that pushes
        events onto a queue; this is what lets fan-out tools' progress callbacks
        (which fire deep inside tool execution, not at a ``yield``) reach the
        consumer live. The producer signals end-of-stream with a ``None`` sentinel.

        A ``ChatSession`` runs one turn at a time — its conversation state is mutable,
        so calling this while a turn is already in flight raises ``RuntimeError``
        rather than silently corrupting history. Run separate conversations on
        separate ``ChatSession`` instances.
        """
        if self._running:
            raise RuntimeError("a turn is already in progress on this ChatSession")
        self._running = True
        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()
        self._active_emit = queue.put_nowait
        task = asyncio.create_task(self._run_to_queue(question, queue))
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
            await task  # surface any exception raised by the producer
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            self._active_emit = None
            self._running = False

    async def run(self, question: ChatInput) -> ChatResult:
        """Non-streaming convenience: run a turn and return its ``ChatResult``.

        Equivalent to draining ``run_stream`` and taking the terminal ``TurnFinished``
        payload — for callers (tests, batch jobs) that want the result, not the live
        events. Cancellation and the one-turn-at-a-time guard behave as in
        ``run_stream``."""
        result: ChatResult | None = None
        async for event in self.run_stream(question):
            if isinstance(event, TurnFinished):
                result = event.result
        if result is not None:
            return result
        raise RuntimeError("run_stream ended without a TurnFinished event")

    async def _run_to_queue(self, question: ChatInput, queue: asyncio.Queue[ChatEvent | None]) -> None:
        """Run the agent loop in the background task, pushing events onto ``queue``
        and a terminating ``None`` sentinel. Uses ``agent.iter()`` so that on
        cancellation we can still snapshot the partial trajectory and accumulated
        usage from the live run."""
        from pydantic_ai import CallToolsNode, ModelRequestNode
        from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

        from tabulaflow.agents.trace import Usage

        emit = queue.put_nowait

        assert self._pydantic_ai_agent is not None

        question = question if isinstance(question, str) else list(question)
        stored_question = describe_chat_input(question)
        message_id = await self._main_scope.add(kind="user_prompt", content=stored_question)
        if message_id is not None:
            question = _shorten_stored_input(question, message_id)

        answer_text = ""
        final_usage: Usage | None = None
        interrupted = False
        completed_normally = False
        completed_results: dict[str, ToolReturnPart] = {}
        text_router = _TextStreamRouter()
        turn_usage = RunUsage()

        try:
            try:
                await self._compact_before_turn(question, turn_usage)
                async with self._pydantic_ai_agent.iter(
                    question,
                    message_history=self._context_messages or None,
                    # Merged over the agent's construction-time settings (per-key,
                    # run level wins). Passed here rather than baked into the agent
                    # so effort-only profile changes never trigger a rebuild.
                    model_settings=self._thinking_settings(),
                    usage=turn_usage,
                ) as agent_run:
                    try:
                        async for node in agent_run:
                            if not isinstance(node, (ModelRequestNode, CallToolsNode)):
                                continue
                            async with node.stream(agent_run.ctx) as stream:
                                async for event in stream:
                                    if isinstance(event, FunctionToolResultEvent) and isinstance(
                                        event.part, ToolReturnPart
                                    ):
                                        completed_results[event.tool_call_id] = event.part
                                    await _emit_stream_event(event, emit, text_router)
                                    await asyncio.sleep(0)
                            emit(UsageUpdated(usage=Usage.from_pydantic_ai_usage(agent_run.usage, self.model)))
                        completed_normally = True
                    except asyncio.CancelledError:
                        interrupted = True
                        raise
                    finally:
                        final_usage = Usage.from_pydantic_ai_usage(agent_run.usage, self.model)
                        partial_messages = list(agent_run.all_messages())
                        new_messages = list(agent_run.new_messages())
                        # Any abnormal exit — user interrupt or an error (LLM API
                        # failure, a tool raising) — can leave the trailing
                        # ModelResponse with unanswered ToolCallParts, which every
                        # provider rejects on the next turn. Patch them either way;
                        # only a clean finish keeps the history verbatim.
                        if completed_normally:
                            self._context_messages = partial_messages
                            self._transcript_messages.extend(new_messages)
                        else:
                            self._context_messages = _patch_incomplete_messages(
                                partial_messages, completed_results, interrupted=interrupted
                            )
                            self._transcript_messages.extend(
                                _patch_incomplete_messages(new_messages, completed_results, interrupted=interrupted)
                            )
                        self._last_usage = final_usage
                        if agent_run.result is not None:
                            answer_text = agent_run.result.output
            finally:
                self._save_trajectory_for_debug()

            # Only reached on normal completion (cancellation re-raised above): emit
            # the authoritative final usage, then the terminal result.
            if final_usage is not None:
                emit(UsageUpdated(usage=final_usage))
            result = await _build_chat_result(answer_text, _declared_bundle(completed_results), self._output_store)
            result.usage = final_usage
            emit(TurnFinished(result=result))
        finally:
            queue.put_nowait(None)  # sentinel: stream exhausted (success, error, or cancel)

    async def _compact_before_turn(self, question: ChatInput, usage: RunUsage) -> None:
        """Checkpoint completed history before a new prompt would exceed its budget."""
        config = self._compaction
        if config is None or not self._context_messages:
            return
        trigger = effective_trigger_tokens(config, self.model)
        if estimate_context_tokens(self._context_messages, question) <= trigger:
            return

        assert self._pydantic_ai_agent is not None
        checkpoint_request = checkpoint_prompt(config)
        emit = self._active_emit
        if emit is not None:
            emit(CompactionStarted())
        try:
            try:
                result = await self._pydantic_ai_agent.run(
                    checkpoint_request,
                    message_history=self._context_messages,
                    model_settings=self._thinking_settings(),
                    usage=usage,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Conversation checkpoint failed; continuing with original history", exc_info=True)
                return

            checkpoint_text = _strip_answer_prefix(result.output)
            response = next(
                (message for message in reversed(result.new_messages()) if message.kind == "response"),
                None,
            )
            if not checkpoint_text or response is None or response.finish_reason == "length":
                logger.warning("Conversation checkpoint was empty or truncated; keeping original history")
                return

            self._transcript_messages.extend(result.new_messages())
            self._context_messages = compact_history(
                self._context_messages,
                checkpoint_request=checkpoint_request,
                checkpoint_text=checkpoint_text,
                config=config,
            )
        finally:
            if emit is not None:
                emit(CompactionFinished())

    def _save_trajectory_for_debug(self) -> None:
        """Persist the latest conversation trajectory to disk, when a
        ``trajectory_log_dir`` was provided (otherwise a no-op)."""
        if self._trajectory_log_dir is None or not self._transcript_messages:
            return
        try:
            from tabulaflow.agents.trace import Trajectory

            trajectory = Trajectory.from_pydantic_ai_messages(self._transcript_messages, id="TRJY-CHAT")
            self._trajectory_log_dir.mkdir(parents=True, exist_ok=True)
            path = self._trajectory_log_dir / "trajectory.md"
            path.write_text(trajectory.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist trajectory debug file")
