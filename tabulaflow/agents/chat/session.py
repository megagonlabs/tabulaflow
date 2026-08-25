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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai.settings import ModelSettings

from tabulaflow.agents.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    MessageStore,
    MessageStoreCapability,
    ScopedMessageStore,
    make_snippet,
)
from tabulaflow.agents.tools.browser.tool import (
    BROWSER_TOOL_NAMES,
    SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
    snapshot_snippet,
)
from tabulaflow.output.formatting._core import format_connector_summary
from tabulaflow.agents.llm import make_agent, make_model_settings, model_display_name
from tabulaflow.agents.chat.events import (
    ChatEvent,
    ChatResult,
    TurnFinished,
    ToolProgress,
    UsageUpdated,
)
from tabulaflow.agents.chat.tools import _ChatTools
from tabulaflow.agents.chat.turn import (
    _TextStreamRouter,
    _build_chat_result,
    _declared_bundle,
    _emit_stream_event,
    _patch_incomplete_messages,
)

if TYPE_CHECKING:
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage, ToolReturnPart

    from tabulaflow.data.registry import DBRegistry
    from tabulaflow.data.sql import SQLConnector
    from tabulaflow.agents.trace import Usage
    from tabulaflow.agents.tools.protocols import ToolProgressUpdate
    from tabulaflow.agents.tools.shell.tool import ExecuteBashTool
    from tabulaflow.output.store import OutputStore

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = files("tabulaflow.agents.chat").joinpath("system_prompt.md").read_text(encoding="utf-8").strip()


DEFAULT_SUBAGENT_MODEL: Final = "openai-responses:gpt-5.4-mini"
DEFAULT_SUBAGENT_REASONING_EFFORT: Final = "medium"
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


@dataclass
class ChatSession:
    """Streaming agent for interactive database chat."""

    registry: DBRegistry
    model: str
    # Reasoning effort for the interactive agent — a unified thinking level
    # (low | medium | high | xhigh) translated per provider by pydantic-ai
    # (OpenAI reasoning_effort, Anthropic thinking budgets / native effort, Gemini
    # thinking_level). Required — callers pass a fully resolved app/research
    # profile rather than relying on ChatSession defaults. Mutable at runtime via
    # ``activate_llm_profile``.
    reasoning_effort: str
    # Session-wide service tier for providers that expose one. Applied to both the
    # root agent and helper LLM calls; ignored by providers without service tiers.
    service_tier: str | None = "priority"
    # Model profile for internal fan-out / extraction subagents. This is separate
    # from the interactive agent: the root conversation may want a large model while
    # hundreds of parallel row/document workers run on a cheaper one.
    subagent_model: str = DEFAULT_SUBAGENT_MODEL
    subagent_reasoning_effort: str = DEFAULT_SUBAGENT_REASONING_EFFORT
    # Host-supplied instructions appended to the baseline prompt — a persona, domain
    # guidance, or frontend-specific phrasing (e.g. slash-command vocabulary). ``None``
    # (default) uses the baseline alone. Composed between the static prefix and the
    # session tail (see ``_compose_system_prompt``), so the large prefix still
    # prompt-caches; keep it stable across a session's turns. A full prompt replacement
    # is intentionally not offered: the baseline ``_SYSTEM_PROMPT`` is half of a contract
    # with this module's tools and answer-marker router, so callers extend rather than swap it.
    extra_instructions: str | None = None
    # Where to persist conversation + subagent trajectories. ``None`` (default)
    # disables all trajectory persistence — set a dir to enable it. Servers leave it
    # off (avoids per-turn disk I/O and cross-conversation clobbering of the single
    # ``trajectory.md``); a single interactive session passes a dir.
    trajectory_log_dir: Path | None = None
    # The session workspace — a SQL scratch DB used to spill query-result DataFrames,
    # offload long messages, and back canonical-name resolution. ``None`` (default)
    # runs in-memory with those persistence features off.
    workspace: SQLConnector | None = None
    # The directory the app was launched from (the user's project, where source data
    # lives) and the agent's transient working area for staging intermediate files.
    # ``None`` (default, e.g. server contexts) disables the host-facing shell/dataset
    # tools that depend on them. Wired in by the app from ``RuntimePaths``.
    project_dir: Path | None = None
    scratch_dir: Path | None = None
    # Directory where ``connect_data_source`` materializes connected sources. ``None``
    # (default, e.g. server contexts) omits that tool. Wired in by the app.
    data_dir: Path | None = None
    last_usage: Usage | None = None
    _message_history: list[ModelMessage] = field(init=False, default_factory=list)
    _system_prompt: str = field(init=False, default=_SYSTEM_PROMPT)
    _pydantic_ai_agent: Agent[None, str] | None = field(init=False, default=None)
    _output_store: OutputStore = field(init=False)
    _message_store: MessageStore = field(init=False)
    _main_scope: ScopedMessageStore = field(init=False)
    _tools: _ChatTools = field(init=False)
    _running: bool = field(init=False, default=False)
    # The active turn's event sink; ``None`` between turns (progress ticks are
    # dropped). Set/cleared by ``run_stream`` alongside ``_running``.
    _active_emit: Callable[[ChatEvent], None] | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        from tabulaflow.agents.tools.protocols import ProgressReportingTool
        from tabulaflow.output.store import OutputStore

        self._output_store = OutputStore(spill_connector=self.workspace, registry=self.registry)
        self._message_store = MessageStore()
        self._main_scope = self._message_store.scoped("main")
        subagent_dir = self.trajectory_log_dir / "subagents" if self.trajectory_log_dir is not None else None
        self._tools = self._build_tools(subagent_dir)
        for tool in self._tools:
            if isinstance(tool, ProgressReportingTool):
                tool.on_progress = self._emit_progress
        if self.workspace is not None:
            self._message_store.attach_connector(self.workspace)
            self._tools.add_canonical_name.attach_connector(self.workspace)
        self._system_prompt = self._compose_system_prompt()
        self._seed_conversation_context()
        self._pydantic_ai_agent = self._make_agent(self.model)

    def _compose_system_prompt(self) -> str:
        """Assemble the agent's instructions: the baseline ``_SYSTEM_PROMPT``, then any
        host ``extra_instructions``, then the ``## Session`` tail. The ordering keeps
        the large static prefix first so it prompt-caches, and the session facts last."""
        parts = [_SYSTEM_PROMPT]
        if self.extra_instructions:
            parts.append(self.extra_instructions.strip())
        session_lines = []
        if self.project_dir is not None:
            session_lines.append(f"- Project directory: {self.project_dir}")
        if self.scratch_dir is not None:
            session_lines.append(f"- Scratch directory: {self.scratch_dir}")
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
        from tabulaflow.agents.tools.create_parameterized_source import CreateParameterizedSourceTool
        from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
        from tabulaflow.agents.tools.filesystem.editor import FileEditorTool
        from tabulaflow.agents.tools.registry.get_column_json_schema import RegistryGetColumnJsonSchemaTool
        from tabulaflow.agents.tools.registry.get_db_document import RegistryGetDBDocumentTool
        from tabulaflow.agents.tools.registry.get_table_schema import RegistryGetTableSchemaTool
        from tabulaflow.agents.tools.registry.run_query import RegistryRunQueryTool
        from tabulaflow.agents.tools.registry.transfer_source_table import TransferSourceTableTool
        from tabulaflow.agents.tools.render_chart import RenderChartTool
        from tabulaflow.agents.tools.render_graph import RenderGraphTool
        from tabulaflow.agents.tools.render_map import RenderMapTool
        from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
        from tabulaflow.agents.tools.show_artifacts import ShowArtifactsTool
        from tabulaflow.agents.tools.browser.tool import WebBrowserTool

        # The fan-out tools operate on the workspace only: sub-tasks are laid out
        # as workspace tables and results written back there (user data reaches
        # them via transfer_source_table). Without a workspace they are disabled.
        run_subagent_for_each_row = None
        extract_rows_from_documents = None
        if self.workspace is not None:
            run_subagent_for_each_row = RunSubagentForEachRowTool(
                self.workspace,
                registry=self.registry,
                message_store=self._message_store,
                subagent_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                store_metadata=True,
                trajectory_log_dir=subagent_dir,
            )
            extract_rows_from_documents = ExtractRowsFromDocumentsTool(
                self.workspace,
                subagent_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                trajectory_log_dir=subagent_dir,
            )

        return _ChatTools(
            run_query=RegistryRunQueryTool(self.registry, output_store=self._output_store, enable_refresh=True),
            create_parameterized_source=CreateParameterizedSourceTool(self.registry, output_store=self._output_store),
            get_db_document=RegistryGetDBDocumentTool(
                self.registry,
                db_summarizer_cls=DBSummarizer,
                db_summarizer_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                enable_refresh=True,
            ),
            get_table_schema=RegistryGetTableSchemaTool(self.registry, SQLDDLSchemaFormatter(), enable_refresh=True),
            get_column_json_schema=RegistryGetColumnJsonSchemaTool(self.registry),
            transfer_source_table=TransferSourceTableTool(self.registry, self._output_store),
            run_subagent_for_each_row=run_subagent_for_each_row,
            extract_rows_from_documents=extract_rows_from_documents,
            connect_data_source=(
                ConnectDataSourceTool(self.registry, self.data_dir) if self.data_dir is not None else None
            ),
            bash=self._build_bash_tool(),
            file_editor=(
                FileEditorTool(
                    str(self.project_dir),
                    message_store=self._main_scope,
                    allowed_roots=None,
                )
                if self.project_dir is not None
                else None
            ),
            apply_patch=(
                ApplyPatchTool(
                    str(self.project_dir),
                    allowed_roots=None,
                )
                if self.project_dir is not None
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
        if self.project_dir is None or self.scratch_dir is None:
            return None
        import os
        import shlex

        if os.name != "posix":
            # The shell tool is POSIX-only (PTY-based). Omit it so the rest of the app
            # still runs on Windows; the agent just loses shell-based gather/transform.
            logger.warning("execute_bash is unavailable on this platform; the agent runs without a shell tool")
            return None

        # The shell tool runs with cwd=project_dir, while in-process run_query/DuckDB
        # resolve relative paths against the live process cwd. The "relative = project
        # dir" design requires these to be equal — assert it loudly rather than silently
        # reading/writing the wrong files if something ever changed cwd.
        if os.path.realpath(os.getcwd()) != os.path.realpath(self.project_dir):
            raise RuntimeError(
                f"process cwd ({os.getcwd()!r}) != project_dir ({str(self.project_dir)!r}); "
                "relative-path resolution would diverge between the shell tool and run_query."
            )

        from tabulaflow.agents.tools.shell.guard import dangerous_command_reason
        from tabulaflow.agents.tools.shell.tool import ExecuteBashTool

        return ExecuteBashTool(
            working_dir=str(self.project_dir),
            init_commands=[f"export SCRATCH={shlex.quote(str(self.scratch_dir))}"],
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
        profile as one readiness boundary. No network request is made.
        """
        return (
            self._api_key_from_model(self._unwrapped_model()),
            self._api_key_from_model(self._subagent_provider_model(self.subagent_model)),
        )

    def _thinking_settings(self) -> ModelSettings:
        """Return the shared provider-specific settings for the interactive model."""
        return make_model_settings(
            model=self.model,
            reasoning_effort=self.reasoning_effort,
            timeout=MAIN_REQUEST_TIMEOUT,
        )

    def _subagent_model_settings(
        self,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> ModelSettings:
        """Model settings for subagent-backed tools.

        Use provider-neutral thinking settings by default. OpenAI Responses gets
        detailed reasoning summaries through the shared reasoning settings helper.
        """
        return make_model_settings(
            model=model or self.subagent_model,
            reasoning_effort=reasoning_effort or self.subagent_reasoning_effort,
            service_tier=self.service_tier,
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

    def _apply_subagent_profile(self, *, model: str, reasoning_effort: str) -> None:
        """Update the tools whose internal helper LLM follows the app subagent profile."""
        from tabulaflow.agents.tools.protocols import LLMProfileTool

        model_settings = self._subagent_model_settings(model=model, reasoning_effort=reasoning_effort)
        for tool in self._tools:
            if isinstance(tool, LLMProfileTool):
                tool.apply_llm_profile(llm=model, model_settings=model_settings)

    def activate_llm_profile(
        self,
        *,
        model: str,
        reasoning_effort: str,
        subagent_model: str,
        subagent_reasoning_effort: str,
    ) -> tuple[str | None, str | None]:
        """Atomically activate main and subagent LLM profiles.

        Conversation, query, tool, and message-store state remain attached to
        this ``ChatSession``. Provider runtimes are prepared before the live
        profile is changed, so a construction failure leaves the old profile
        usable. A main-model change is recorded in the conversation history
        (see ``_note_model_change``). Returns the API keys resolved during
        preparation.
        """
        if self._running:
            raise RuntimeError("cannot change the LLM profile during an active turn")
        unchanged = (
            self.model == model
            and self.reasoning_effort == reasoning_effort
            and self.subagent_model == subagent_model
            and self.subagent_reasoning_effort == subagent_reasoning_effort
        )

        runtime_agent = self._pydantic_ai_agent
        if self.model != model:
            runtime_agent = self._make_agent(model)
        subagent_provider_model = self._subagent_provider_model(subagent_model)
        keys = (
            self._api_key_from_model(self._unwrap_model(runtime_agent.model) if runtime_agent is not None else None),
            self._api_key_from_model(subagent_provider_model),
        )
        if unchanged:
            return keys

        previous_model = self.model
        previous_subagent_model = self.subagent_model
        previous_subagent_effort = self.subagent_reasoning_effort
        try:
            self._apply_subagent_profile(
                model=subagent_model,
                reasoning_effort=subagent_reasoning_effort,
            )
        except Exception:
            self._apply_subagent_profile(
                model=previous_subagent_model,
                reasoning_effort=previous_subagent_effort,
            )
            raise
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.subagent_model = subagent_model
        self.subagent_reasoning_effort = subagent_reasoning_effort
        self._pydantic_ai_agent = runtime_agent
        if model != previous_model:
            self._note_model_change(previous_model, model)
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

        self._message_history.append(ModelRequest(parts=[UserPromptPart(content=f"[system: {description}]")]))

    def _note_model_change(self, previous: str, current: str) -> None:
        """Record a main-model switch in the conversation history."""
        description = (
            "the model powering this conversation changed from "
            f"{model_display_name(previous)} to {model_display_name(current)}"
        )
        self.note_event(description + ".")

    def _note_initial_registry(self) -> None:
        aliases = self.registry.list_aliases()
        if not aliases:
            return

        entries = []
        for alias in aliases:
            try:
                connector = self.registry.get(alias)
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
        self._message_history.clear()
        self.last_usage = None
        self._seed_conversation_context()

    async def aclose(self) -> None:
        """Release session-scoped resources — currently the persistent shell session."""
        if self._tools.bash is not None:
            await self._tools.bash.close()

    def _make_agent(self, model: str) -> Agent[None, str]:
        """Construct the model-specific runtime around the session's live tools."""
        from tabulaflow.agents.tools.run_subagent_for_each_row import ReleaseBrowserBeforeFanout

        tools: list[Any] = []
        for tool in self._tools:
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
            model_settings=make_model_settings(model=model, service_tier=self.service_tier),
        )

    async def run_stream(self, question: str) -> AsyncIterator[ChatEvent]:
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

    async def run(self, question: str) -> ChatResult:
        """Non-streaming convenience: run a turn and return its ``ChatResult``.

        Equivalent to draining ``run_stream`` and taking the terminal ``TurnFinished``
        payload — for callers (tests, batch jobs) that want the result, not the live
        events. Cancellation and the one-turn-at-a-time guard behave as in
        ``run_stream``."""
        async for event in self.run_stream(question):
            if isinstance(event, TurnFinished):
                return event.result
        raise RuntimeError("run_stream ended without a TurnFinished event")

    async def _run_to_queue(self, question: str, queue: asyncio.Queue[ChatEvent | None]) -> None:
        """Run the agent loop in the background task, pushing events onto ``queue``
        and a terminating ``None`` sentinel. Uses ``agent.iter()`` so that on
        cancellation we can still snapshot the partial trajectory and accumulated
        usage from the live run."""
        from pydantic_ai import CallToolsNode, ModelRequestNode
        from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

        from tabulaflow.agents.trace import Usage

        emit = queue.put_nowait

        assert self._pydantic_ai_agent is not None

        message_id = await self._main_scope.add(kind="user_prompt", content=question)
        if len(question) > MESSAGE_THRESHOLD_CHARS:
            question = make_snippet(message_id, question)

        answer_text = ""
        final_usage: Usage | None = None
        interrupted = False
        completed_normally = False
        completed_results: dict[str, ToolReturnPart] = {}
        text_router = _TextStreamRouter()

        try:
            try:
                async with self._pydantic_ai_agent.iter(
                    question,
                    message_history=self._message_history or None,
                    # Merged over the agent's construction-time settings (per-key,
                    # run level wins). Passed here rather than baked into the agent
                    # so effort-only profile changes never trigger a rebuild.
                    model_settings=self._thinking_settings(),
                ) as agent_run:
                    try:
                        async for node in agent_run:
                            if not isinstance(node, (ModelRequestNode, CallToolsNode)):
                                continue
                            async with node.stream(agent_run.ctx) as stream:
                                async for event in stream:
                                    if isinstance(event, FunctionToolResultEvent) and isinstance(
                                        event.result, ToolReturnPart
                                    ):
                                        completed_results[event.tool_call_id] = event.result
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
                        # Any abnormal exit — user interrupt or an error (LLM API
                        # failure, a tool raising) — can leave the trailing
                        # ModelResponse with unanswered ToolCallParts, which every
                        # provider rejects on the next turn. Patch them either way;
                        # only a clean finish keeps the history verbatim.
                        if completed_normally:
                            self._message_history = partial_messages
                        else:
                            self._message_history = _patch_incomplete_messages(
                                partial_messages, completed_results, interrupted=interrupted
                            )
                        self.last_usage = final_usage
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

    def _save_trajectory_for_debug(self) -> None:
        """Persist the latest conversation trajectory to disk, when a
        ``trajectory_log_dir`` was provided (otherwise a no-op)."""
        if self.trajectory_log_dir is None or not self._message_history:
            return
        try:
            from tabulaflow.agents.trace import Trajectory

            trajectory = Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-CHAT")
            self.trajectory_log_dir.mkdir(parents=True, exist_ok=True)
            path = self.trajectory_log_dir / "trajectory.md"
            path.write_text(trajectory.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist trajectory debug file")
