"""CLI chat agent for interactive query chat."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterable
from datetime import date
from importlib.resources import files
import json
import logging
from pathlib import Path
import re
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai.settings import ModelSettings

from tabulaflow.toolhub.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    MessageStore,
    MessageStoreCapability,
    ScopedMessageStore,
    make_snippet,
)
from tabulaflow.toolhub.web_browser import (
    BROWSER_TOOL_NAMES,
    SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
    snapshot_snippet,
)
from tabulaflow.core.db_connector import connector_info
from tabulaflow.core.llm import make_agent, make_model_settings, model_display_name
from tabulaflow.chat.result import ChatResult, ChatResultChart, ChatResultGraph, ChatResultMap, ChatResultRecord
from tabulaflow.chat.events import (
    ChatEvent,
    ColumnsReturned,
    AnswerDelta,
    Completed,
    Failed,
    Finished,
    NarrationDelta,
    RowsReturned,
    ThinkingDelta,
    ToolFinished,
    ToolOutcome,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)

if TYPE_CHECKING:
    import pandas as pd
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage, ToolReturnPart

    from tabulaflow.core.db_connector.db_registry import DBRegistry
    from tabulaflow.core.db_connector.sql_conn import SQLConnector
    from tabulaflow.core.types import Usage
    from tabulaflow.toolhub import (
        AddCanonicalNameTool,
        ApplyPatchTool,
        ChartArtifact,
        ConnectDataSourceTool,
        ExecuteBashTool,
        ExtractRowsFromDocumentsTool,
        FileEditorTool,
        GraphArtifact,
        LLMProfileTool,
        MapArtifact,
        QueryHistory,
        QueryRecord,
        RegistryGetColumnJsonSchemaTool,
        RegistryGetDBDocumentTool,
        RegistryGetTableSchemaTool,
        RegistryRunQueryTool,
        RegistryTransferRecordTool,
        RenderChartTool,
        RenderGraphTool,
        RenderMapTool,
        RunSubagentForEachRowTool,
        WebBrowserTool,
    )

logger = logging.getLogger(__name__)

_ARTIFACT_REF_RE = re.compile(r"\[\[artifact:((?:Q|CHART|MAP|GRAPH)\d+)(?::([^\]]+))?\]\]")


SYSTEM_PROMPT = files("tabulaflow.chat").joinpath("system_prompt.md").read_text(encoding="utf-8").strip()


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


def _model_supports_apply_patch(model: str) -> bool:
    provider, _, model_name = model.partition(":")
    return provider == "openai-responses" and model_name.startswith("gpt-5")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class _Toolset:
    """Typed bundle of agent tools (internal to ``ChatAgent``)."""

    run_query: RegistryRunQueryTool
    get_db_document: RegistryGetDBDocumentTool
    get_column_json_schema: RegistryGetColumnJsonSchemaTool
    get_table_schema: RegistryGetTableSchemaTool
    transfer_record: RegistryTransferRecordTool
    # The fan-out tools are bound to the session workspace (the only DB they may
    # read from and write to); ``None`` when the agent runs without a workspace.
    run_subagent_for_each_row: RunSubagentForEachRowTool | None
    extract_rows_from_documents: ExtractRowsFromDocumentsTool | None
    add_canonical_name: AddCanonicalNameTool
    render_chart: RenderChartTool
    render_graph: RenderGraphTool
    render_map: RenderMapTool
    web_browser: WebBrowserTool
    # Host-facing tools; ``None`` when the app didn't supply the dirs they need.
    connect_data_source: ConnectDataSourceTool | None
    bash: ExecuteBashTool | None
    file_editor: FileEditorTool | None
    apply_patch: ApplyPatchTool | None


@dataclass
class ChatAgent:
    """Streaming agent for interactive database chat."""

    registry: DBRegistry
    model: str
    # Reasoning effort for the interactive agent — a unified thinking level
    # (low | medium | high | xhigh) translated per provider by pydantic-ai
    # (OpenAI reasoning_effort, Anthropic thinking budgets / native effort, Gemini
    # thinking_level). Required — callers pass a fully resolved app/research
    # profile rather than relying on ChatAgent defaults. Mutable at runtime via
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
    # is intentionally not offered: the baseline ``SYSTEM_PROMPT`` is half of a contract
    # with this module's tools and citation parser, so callers extend rather than swap it.
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
    _system_prompt: str = field(init=False, default=SYSTEM_PROMPT)
    _pydantic_ai_agent: Agent[None, str] | None = field(init=False, default=None)
    _query_history: QueryHistory = field(init=False)
    _message_store: MessageStore = field(init=False)
    _main_scope: ScopedMessageStore = field(init=False)
    _tools: _Toolset = field(init=False)
    _running: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        from tabulaflow.toolhub import QueryHistory

        self._query_history = QueryHistory(spill_connector=self.workspace)
        self._message_store = MessageStore()
        self._main_scope = self._message_store.scoped("main")
        subagent_dir = self.trajectory_log_dir / "subagents" if self.trajectory_log_dir is not None else None
        self._tools = self._build_tools(subagent_dir)
        if self.workspace is not None:
            self._message_store.attach_connector(self.workspace)
            self._tools.add_canonical_name.attach_connector(self.workspace)
        self._system_prompt = self._compose_system_prompt()
        self.note_event(f"the model powering this conversation is {model_display_name(self.model)}.")
        self._note_initial_registry()
        self._pydantic_ai_agent = self._make_agent(self.model)

    def _compose_system_prompt(self) -> str:
        """Assemble the agent's instructions: the baseline ``SYSTEM_PROMPT``, then any
        host ``extra_instructions``, then the ``## Session`` tail. The ordering keeps
        the large static prefix first so it prompt-caches, and the session facts last."""
        parts = [SYSTEM_PROMPT]
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

    def _build_tools(self, subagent_dir: Path | None) -> _Toolset:
        """Construct the agent's toolset, wiring in the shared query history and
        message store. ``subagent_dir`` (if set) is where subagent trajectories land."""
        from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
        from tabulaflow.modulehub.db_summarizer import DBSummarizer
        from tabulaflow.toolhub import (
            AddCanonicalNameTool,
            ApplyPatchTool,
            ConnectDataSourceTool,
            ExtractRowsFromDocumentsTool,
            FileEditorTool,
            RegistryGetColumnJsonSchemaTool,
            RegistryGetDBDocumentTool,
            RegistryGetTableSchemaTool,
            RegistryRunQueryTool,
            RegistryTransferRecordTool,
            RenderChartTool,
            RenderGraphTool,
            RenderMapTool,
            RunSubagentForEachRowTool,
            WebBrowserTool,
        )

        # The fan-out tools operate on the workspace only: sub-tasks are laid out
        # as workspace tables and results written back there (user data reaches
        # them via transfer_record). Without a workspace they are disabled.
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

        return _Toolset(
            run_query=RegistryRunQueryTool(self.registry, history=self._query_history, enable_refresh=True),
            get_db_document=RegistryGetDBDocumentTool(
                self.registry,
                db_summarizer_cls=DBSummarizer,
                db_summarizer_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                enable_refresh=True,
            ),
            get_column_json_schema=RegistryGetColumnJsonSchemaTool(self.registry),
            get_table_schema=RegistryGetTableSchemaTool(self.registry, SQLDDLSchemaFormatter(), enable_refresh=True),
            transfer_record=RegistryTransferRecordTool(self.registry, self._query_history),
            run_subagent_for_each_row=run_subagent_for_each_row,
            extract_rows_from_documents=extract_rows_from_documents,
            add_canonical_name=AddCanonicalNameTool(
                subagent_llm=self.subagent_model,
                model_settings=self._subagent_model_settings(),
                trajectory_log_dir=subagent_dir,
            ),
            render_chart=RenderChartTool(history=self._query_history),
            render_graph=RenderGraphTool(history=self._query_history),
            render_map=RenderMapTool(history=self._query_history),
            web_browser=WebBrowserTool(),
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

        from tabulaflow.toolhub import ExecuteBashTool
        from tabulaflow.toolhub.engines.shell_guard import dangerous_command_reason

        return ExecuteBashTool(
            working_dir=str(self.project_dir),
            init_commands=[f"export SCRATCH={shlex.quote(str(self.scratch_dir))}"],
            command_filter=dangerous_command_reason,
        )

    @property
    def query_history(self) -> QueryHistory:
        """The live query history — results the agent's answers reference."""
        return self._query_history

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

    def _subagent_profile_tools(self) -> tuple[LLMProfileTool, ...]:
        """Tools whose internal helper LLM follows the app subagent profile."""
        tools: list[LLMProfileTool] = [self._tools.get_db_document, self._tools.add_canonical_name]
        if self._tools.run_subagent_for_each_row is not None:
            tools.append(self._tools.run_subagent_for_each_row)
        if self._tools.extract_rows_from_documents is not None:
            tools.append(self._tools.extract_rows_from_documents)
        return tuple(tools)

    def _apply_subagent_profile(self, *, model: str, reasoning_effort: str) -> None:
        """Update existing subagent-backed tool instances with the supplied profile."""
        model_settings = self._subagent_model_settings(model=model, reasoning_effort=reasoning_effort)
        for tool in self._subagent_profile_tools():
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
        this ``ChatAgent``. Provider runtimes are prepared before the live
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
        """Record a main-model switch in the conversation so the incoming model
        doesn't blindly imitate the tool-use patterns in history when its own
        toolset differs. The note states facts only (the switch and any tool
        availability delta); tool preferences live in the tool descriptions,
        which ship exactly when the tool does."""
        description = (
            "the model powering this conversation changed from "
            f"{model_display_name(previous)} to {model_display_name(current)}"
        )
        if self._tools.apply_patch is not None:
            had = _model_supports_apply_patch(previous)
            has = _model_supports_apply_patch(current)
            if has and not had:
                description += "; the apply_patch tool is now available"
            elif had and not has:
                description += "; the apply_patch tool is no longer available"
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
            entries.append(f"`{alias}` ({connector_info(connector)})")

        if entries:
            self.note_event("the following data sources are already registered: " + ", ".join(entries) + ".")

    async def aclose(self) -> None:
        """Release session-scoped resources — currently the persistent shell session."""
        if self._tools.bash is not None:
            await self._tools.bash.close()

    def _make_agent(self, model: str) -> Agent[None, str]:
        """Construct the model-specific runtime around the session's live tools."""
        from tabulaflow.toolhub.run_subagent_for_each_row import ReleaseBrowserBeforeFanout

        fanout_tools = [
            tool.as_pydantic_ai_tool()
            for tool in (self._tools.run_subagent_for_each_row, self._tools.extract_rows_from_documents)
            if tool is not None
        ]
        apply_patch_tool = self._tools.apply_patch if _model_supports_apply_patch(model) else None
        host_tools = [
            tool.as_pydantic_ai_tool()
            for tool in (
                self._tools.connect_data_source,
                self._tools.bash,
                self._tools.file_editor,
                apply_patch_tool,
            )
            if tool is not None
        ]
        return make_agent(
            model,
            tools=[
                self._tools.run_query.as_pydantic_ai_tool(),
                self._tools.get_db_document.as_pydantic_ai_tool(),
                self._tools.get_table_schema.as_pydantic_ai_tool(),
                self._tools.get_column_json_schema.as_pydantic_ai_tool(),
                self._tools.transfer_record.as_pydantic_ai_tool(),
                *fanout_tools,
                *host_tools,
                self._tools.add_canonical_name.as_pydantic_ai_tool(),
                self._tools.render_chart.as_pydantic_ai_tool(),
                self._tools.render_graph.as_pydantic_ai_tool(),
                self._tools.render_map.as_pydantic_ai_tool(),
                *self._tools.web_browser.as_pydantic_ai_tools(),
            ],
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

        The stream ends with exactly one ``Finished`` (carrying the ``ChatResult``)
        on normal completion. Failures propagate as exceptions. To interrupt, cancel
        the task iterating this generator: it raises ``CancelledError`` and the
        agent's message history / ``last_usage`` are left reflecting the partial run.

        The agent loop runs as a background task (``_run_to_queue``) that pushes
        events onto a queue; this is what lets fan-out tools' progress callbacks
        (which fire deep inside tool execution, not at a ``yield``) reach the
        consumer live. The producer signals end-of-stream with a ``None`` sentinel.

        A ``ChatAgent`` runs one turn at a time — its conversation state is mutable,
        so calling this while a turn is already in flight raises ``RuntimeError``
        rather than silently corrupting history. Run separate conversations on
        separate ``ChatAgent`` instances.
        """
        if self._running:
            raise RuntimeError("a turn is already in progress on this ChatAgent")
        self._running = True
        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()
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
            self._running = False

    async def run(self, question: str) -> ChatResult:
        """Non-streaming convenience: run a turn and return its ``ChatResult``.

        Equivalent to draining ``run_stream`` and taking the terminal ``Finished``
        payload — for callers (tests, batch jobs) that want the result, not the live
        events. Cancellation and the one-turn-at-a-time guard behave as in
        ``run_stream``."""
        async for event in self.run_stream(question):
            if isinstance(event, Finished):
                return event.result
        raise RuntimeError("run_stream ended without a Finished event")

    async def _run_to_queue(self, question: str, queue: asyncio.Queue[ChatEvent | None]) -> None:
        """Run the agent loop in the background task, pushing events onto ``queue``
        and a terminating ``None`` sentinel. Uses ``agent.iter()`` so that on
        cancellation we can still snapshot the partial trajectory and accumulated
        usage from the live run."""
        from pydantic_ai import CallToolsNode, ModelRequestNode
        from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

        from tabulaflow.core.types import Usage

        emit = queue.put_nowait
        # Each fan-out tool passes its tool_call_id so the UI can route concurrent
        # tools' progress to the right step.
        if self._tools.run_subagent_for_each_row is not None:
            self._tools.run_subagent_for_each_row.on_row_complete = lambda c, t, tcid: emit(
                ToolProgress(completed=c, total=t, tool_call_id=tcid)
            )
        if self._tools.extract_rows_from_documents is not None:
            self._tools.extract_rows_from_documents.on_rows_extracted = lambda c, tcid: emit(
                ToolProgress(completed=c, total=None, unit="rows", tool_call_id=tcid)
            )
        self._tools.add_canonical_name.on_progress = lambda stage, c, t, tcid: emit(
            ToolProgress(completed=c, total=t, stage=stage, tool_call_id=tcid)
        )

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
                                    await _emit_stream_event(
                                        event,
                                        emit,
                                        self._query_history,
                                        self._tools.get_table_schema,
                                        text_router,
                                    )
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
                if self._tools.run_subagent_for_each_row is not None:
                    self._tools.run_subagent_for_each_row.on_row_complete = None
                if self._tools.extract_rows_from_documents is not None:
                    self._tools.extract_rows_from_documents.on_rows_extracted = None
                self._tools.add_canonical_name.on_progress = None
                self._save_trajectory_for_debug()

            # Only reached on normal completion (cancellation re-raised above): emit
            # the authoritative final usage, then the terminal result.
            if final_usage is not None:
                emit(UsageUpdated(usage=final_usage))
            result = await _build_chat_result(answer_text, self._query_history)
            result.usage = final_usage
            emit(Finished(result=result))
        finally:
            queue.put_nowait(None)  # sentinel: stream exhausted (success, error, or cancel)

    def _save_trajectory_for_debug(self) -> None:
        """Persist the latest conversation trajectory to disk, when a
        ``trajectory_log_dir`` was provided (otherwise a no-op)."""
        if self.trajectory_log_dir is None or not self._message_history:
            return
        try:
            from tabulaflow.core.types import Trajectory

            trajectory = Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-CHAT")
            self.trajectory_log_dir.mkdir(parents=True, exist_ok=True)
            path = self.trajectory_log_dir / "trajectory.md"
            path.write_text(trajectory.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist trajectory debug file")


async def _build_chat_result(
    answer_text: str,
    query_history: QueryHistory,
) -> ChatResult:
    display_text, refs = _extract_result_refs(answer_text)
    artifacts = await _artifacts_from_refs(refs, query_history)
    primary_artifact_index: int | None = 0 if artifacts else None
    return ChatResult(text=display_text, artifacts=artifacts, primary_artifact_index=primary_artifact_index)


def _patch_incomplete_messages(
    messages: list[ModelMessage],
    completed_results: dict[str, ToolReturnPart],
    *,
    interrupted: bool,
) -> list[ModelMessage]:
    """Make ``messages`` valid as ``message_history`` for the next agent run.

    A run that ends before completing — the user interrupts it, or it raises
    (an LLM API failure, a tool error) — leaves the trailing ``ModelResponse``
    with unanswered ``ToolCallPart``s, because pydantic-ai's ``CallToolsNode``
    only appends the aggregated tool-return ``ModelRequest`` once all tools
    finish. Every provider rejects a tool call with no matching result, so each
    pending call must be answered: with its real ``ToolReturnPart`` if the result
    event reached us before the break, otherwise a synthetic placeholder. A
    trailing system turn records why the run stopped. ``interrupted`` selects
    the wording (user cancel vs. error).
    """
    from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart

    cause = "was interrupted by the user" if interrupted else "failed with an error"

    out = list(messages)
    last = out[-1] if out else None
    pending = [p for p in last.parts if isinstance(p, ToolCallPart)] if isinstance(last, ModelResponse) else []

    if pending:
        out.append(
            ModelRequest(
                parts=[
                    completed_results.get(p.tool_call_id)
                    or ToolReturnPart(
                        tool_name=p.tool_name,
                        tool_call_id=p.tool_call_id,
                        content=(
                            f"[system: the run {cause} before this result was captured. "
                            "The tool may have completed first — any side effects "
                            "(e.g. writes) may or may not have taken effect.]"
                        ),
                    )
                    for p in pending
                ]
            )
        )
    out.append(ModelRequest(parts=[UserPromptPart(content=f"[system: the previous run {cause}.]")]))
    return out


_ARTIFACTS_OPEN = "<artifacts>"
_ARTIFACTS_CLOSE = "</artifacts>"


def _parse_refs(text: str) -> list[tuple[str, str | None]]:
    """Extract ``(record_id, label)`` pairs from ``[[artifact:Q<id>:<label>]]`` markers
    (label normalized to ``None`` when absent or blank)."""
    return [(m.group(1), (m.group(2) or "").strip() or None) for m in _ARTIFACT_REF_RE.finditer(text)]


def _extract_result_refs(answer_text: str) -> tuple[str, list[tuple[str, str | None]]]:
    close_start = answer_text.find(_ARTIFACTS_CLOSE)
    open_start = answer_text.find(_ARTIFACTS_OPEN)
    if open_start != -1 and close_start > open_start:
        block_start = open_start + len(_ARTIFACTS_OPEN)
        block = answer_text[block_start:close_start]
        display_text = answer_text[close_start + len(_ARTIFACTS_CLOSE) :]
        refs = _parse_refs(block)
        # Refs belong inside the block, but the model occasionally cites inline;
        # strip those markers from the prose and still resolve them.
        seen = {record_id for record_id, _ in refs}
        for ref in _parse_refs(display_text):
            if ref[0] not in seen:
                refs.append(ref)
                seen.add(ref[0])
        return _ARTIFACT_REF_RE.sub("", display_text).strip(), refs

    # No recognized artifact block: the whole output is user-facing. Still strip
    # any inline ``[[artifact:...]]`` markers the agent may have left in the prose.
    refs = _parse_refs(answer_text)
    if refs:
        answer_text = _ARTIFACT_REF_RE.sub("", answer_text)
    return answer_text.strip(), refs


class _TextStreamRouter:
    """Routes a streamed text run into the final answer vs. mid-turn narration, and
    strips the artifact refs block from the answer.

    A run that opens with an ``<artifacts>...</artifacts>`` block is the **answer**:
    held back until the closing tag, then the text after it streams. Any other run is
    **narration** and streams live. After the first chunk that yields text,
    :attr:`is_answer` says which it is. Reset via :meth:`reset` per text part.

    Kept here (not the frontend) so the artifact-block convention — owned by this
    agent's prompt — never crosses the layer boundary.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._raw = ""
        self._open = False  # True once text has begun streaming
        self.is_answer = False  # whether the opened run is the final answer

    def feed(self, chunk: str) -> str:
        """Accumulate ``chunk``; return its newly emittable text (``""`` until known).
        Once non-empty, :attr:`is_answer` is set for the run."""
        self._raw += chunk
        if self._open:
            return chunk

        close_start = self._raw.find(_ARTIFACTS_CLOSE)
        open_start = self._raw.find(_ARTIFACTS_OPEN)
        if open_start != -1 and close_start > open_start:
            answer = self._raw[close_start + len(_ARTIFACTS_CLOSE) :].lstrip("\n")
            if not answer:
                return ""  # artifact block complete but answer hasn't started yet
            self._open = True
            self.is_answer = True
            return answer

        stripped = self._raw.lstrip()
        if _ARTIFACTS_OPEN.startswith(stripped):
            return ""
        if stripped and not stripped.startswith(_ARTIFACTS_OPEN):
            self._open = True
            self.is_answer = False
            return self._raw  # narration (or an answer the model failed to delimit)
        return ""


async def _artifacts_from_refs(
    refs: Iterable[tuple[str, str | None]],
    query_history: QueryHistory,
) -> list[ChatResultRecord | ChatResultChart | ChatResultMap | ChatResultGraph]:
    """Resolve citation refs into display artifacts, preserving citation order."""
    artifacts: list[ChatResultRecord | ChatResultChart | ChatResultMap | ChatResultGraph] = []
    for ref_id, label in refs:
        if ref_id.startswith("CHART"):
            try:
                chart_artifact = query_history.get_chart(ref_id)
            except (KeyError, ValueError):
                continue
            artifacts.append(await _chat_result_chart_from_artifact(chart_artifact, label, query_history))
        elif ref_id.startswith("MAP"):
            try:
                map_artifact = query_history.get_map(ref_id)
            except (KeyError, ValueError):
                continue
            artifacts.append(await _chat_result_map_from_artifact(map_artifact, label, query_history))
        elif ref_id.startswith("GRAPH"):
            try:
                graph_artifact = query_history.get_graph(ref_id)
            except (KeyError, ValueError):
                continue
            artifacts.append(await _chat_result_graph_from_artifact(graph_artifact, label, query_history))
        else:
            try:
                query_record = await query_history.get(ref_id)
            except (KeyError, ValueError):
                continue
            artifacts.append(_chat_result_record_from_query_record(query_record, label))
    return artifacts


async def _chat_result_chart_from_artifact(
    chart_artifact: ChartArtifact,
    label: str | None,
    query_history: QueryHistory,
) -> ChatResultChart:
    """Resolve a stored chart artifact's source record into a display record."""
    query: str | None = None
    df: pd.DataFrame | None = None
    query_lexer = "sql"
    try:
        record = await query_history.get(chart_artifact.record_id)
    except (KeyError, ValueError):
        record = None
    if record is not None:
        query = record.pred_query.query
        if record.pred_query.exec_result is not None:
            df = record.pred_query.exec_result.df
        query_lexer = "cypher" if record.connector_type == "property_graph" else "sql"
    return ChatResultChart(
        chart_id=chart_artifact.chart_id,
        label=label,
        chart_spec=chart_artifact.chart_spec,
        record_id=chart_artifact.record_id,
        query=query,
        df=df,
        query_lexer=query_lexer,
    )


async def _chat_result_map_from_artifact(
    map_artifact: MapArtifact,
    label: str | None,
    query_history: QueryHistory,
) -> ChatResultMap:
    """Resolve a stored map artifact's per-source DataFrames into a display record."""
    spec = map_artifact.map_spec
    layers = spec.get("layers") or []
    source_ids: list[str] = []
    for layer in layers:
        sid = layer.get("source") if isinstance(layer, dict) else None
        if sid and sid not in source_ids:
            source_ids.append(sid)
    sources: dict[str, pd.DataFrame] = {}
    for sid in source_ids:
        try:
            record = await query_history.get(sid)
        except (KeyError, ValueError):
            continue
        exec_result = record.pred_query.exec_result
        if exec_result is not None and exec_result.df is not None:
            sources[sid] = exec_result.df
    return ChatResultMap(map_id=map_artifact.map_id, label=label, map_spec=spec, sources=sources)


async def _chat_result_graph_from_artifact(
    graph_artifact: GraphArtifact,
    label: str | None,
    query_history: QueryHistory,
) -> ChatResultGraph:
    """Resolve a stored graph artifact's per-source DataFrames into a display record."""
    spec = graph_artifact.graph_spec
    source_ids: list[str] = []
    for key in ("nodes", "edges"):
        entries = spec.get(key) or []
        for entry in entries:
            rid = entry.get("record_id") if isinstance(entry, dict) else None
            if rid and rid not in source_ids:
                source_ids.append(rid)
    sources: dict[str, pd.DataFrame] = {}
    for sid in source_ids:
        try:
            record = await query_history.get(sid)
        except (KeyError, ValueError):
            continue
        exec_result = record.pred_query.exec_result
        if exec_result is not None and exec_result.df is not None:
            sources[sid] = exec_result.df
    return ChatResultGraph(graph_id=graph_artifact.graph_id, label=label, graph_spec=spec, sources=sources)


def _chat_result_record_from_query_record(
    query_record: QueryRecord,
    label: str | None,
) -> ChatResultRecord:
    pred = query_record.pred_query
    return ChatResultRecord(
        record_id=query_record.record_id,
        label=label,
        query=pred.query,
        df=pred.exec_result.df if pred.exec_result else None,
        query_lexer="cypher" if query_record.connector_type == "property_graph" else "sql",
    )


# ---------------------------------------------------------------------------
# Stream event handlers
# ---------------------------------------------------------------------------


async def _emit_stream_event(
    event: object,
    emit: Callable[[ChatEvent], None],
    query_history: QueryHistory,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
    text_router: "_TextStreamRouter",
) -> None:
    """Map one pydantic-ai stream event to ``ChatEvent``s and emit them.

    Events carry structured data only: ``ToolStarted.args`` is the raw call args
    (a frontend renders them); ``ToolFinished.outcome`` is the structured
    ``ToolOutcome`` (built here because it needs the agent's query history).

    Text and reasoning each arrive as a ``PartStartEvent`` (the first chunk — its
    content is non-empty on content-bearing streaming providers) followed by
    ``PartDeltaEvent``s. Both points must be handled or the first chunk is dropped.
    """
    from pydantic_ai.messages import (
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        PartDeltaEvent,
        PartStartEvent,
        TextPart,
        TextPartDelta,
        ThinkingPart,
        ThinkingPartDelta,
        ToolReturnPart,
    )

    if isinstance(event, FunctionToolCallEvent):
        emit(
            ToolStarted(tool_call_id=event.tool_call_id, name=event.part.tool_name, args=_coerce_args(event.part.args))
        )

    elif isinstance(event, FunctionToolResultEvent):
        tool_name = event.result.tool_name or ""
        result_part = event.result if isinstance(event.result, ToolReturnPart) else None
        outcome = await _build_outcome(tool_name, query_history, get_table_schema_tool, result_part)
        emit(ToolFinished(tool_call_id=event.tool_call_id, name=tool_name, outcome=outcome))

    elif isinstance(event, PartStartEvent):
        part = event.part
        if isinstance(part, ThinkingPart) and part.content:
            emit(ThinkingDelta(content=part.content))
        elif isinstance(part, TextPart):
            text_router.reset()  # a new text part begins a fresh run
            visible = text_router.feed(part.content) if part.content else ""
            if visible:
                emit((AnswerDelta if text_router.is_answer else NarrationDelta)(content=visible))

    elif isinstance(event, PartDeltaEvent):
        delta = event.delta
        if isinstance(delta, ThinkingPartDelta) and delta.content_delta:
            emit(ThinkingDelta(content=delta.content_delta))
        elif isinstance(delta, TextPartDelta) and delta.content_delta:
            visible = text_router.feed(delta.content_delta)
            if visible:
                emit((AnswerDelta if text_router.is_answer else NarrationDelta)(content=visible))


def _coerce_args(args: object) -> dict[str, Any]:
    """Normalize a tool call's ``args`` (pydantic-ai gives a JSON string or dict) to a dict."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return {}
    return args if isinstance(args, dict) else {}


async def _build_outcome(
    tool_name: str,
    query_history: QueryHistory,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
    result_part: ToolReturnPart | None = None,
) -> ToolOutcome:
    """Derive the structured tool outcome from the agent's recorded state. Only
    ``run_query`` (rows / error) and ``get_table_schema`` (columns) report a count;
    everything else is ``Completed``. See ``chat.events`` for the tool→outcome map."""
    if tool_name == "run_query":
        try:
            record = await query_history.last()
            pred = record.pred_query
            if pred.exec_result and pred.exec_result.df is not None:
                return RowsReturned(count=len(pred.exec_result.df))
            if pred.exec_result and pred.exec_result.error:
                return Failed()
        except ValueError:
            pass
    if tool_name == "get_table_schema" and get_table_schema_tool is not None:
        n = get_table_schema_tool.last_columns_returned
        if n is not None:
            return ColumnsReturned(count=n)
    content = result_part.content if result_part is not None else None
    if isinstance(content, str) and content.startswith("(error:"):
        return Failed()
    return Completed()
