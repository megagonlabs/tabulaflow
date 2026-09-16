# Agents

Build stateful chat agents with structured results and streaming events, or
use tools, document extraction, data enrichment, and data-source summarization
in your own workflows.

## Chat sessions

Import `ChatSession` and `ChatInput` from `tabulaflow.agents`.

A session runs one turn at a time. `run(...)` returns a `ChatResult`;
`run_stream(...)` yields semantic events and ends with `TurnFinished` on
normal completion. Failures and cancellation propagate as exceptions.
Close the session with `aclose()` and close the connectors owned by your
application separately.

For interruption, cancel and await the task consuming the stream before
starting another turn. `reset_conversation()` clears conversation context
while keeping connectors and stored outputs. Automatic context compaction
is enabled by default; pass `compaction=None` to disable it.

::: tabulaflow.agents.chat.session.ChatSession
    options:
      members:
        - run
        - run_stream
        - output_store
        - last_usage
        - model
        - reasoning
        - subagent_model
        - subagent_reasoning
        - activate_llm_profile
        - note_event
        - reset_conversation
        - aclose

::: tabulaflow.agents.chat.input.ChatInput

::: tabulaflow.agents.chat.compaction.CompactionConfig

## Events and turn results

These types are also available from `tabulaflow.agents.chat`.

`ToolStarted` identifies a tool call, `AnswerDelta` carries answer text, and
`TurnFinished` carries the complete result. Other events report narration,
tool progress, usage, and context compaction.

::: tabulaflow.agents.chat.events
    options:
      show_root_heading: false
      heading_level: 2
      members:
        - ChatResult
        - ChatEvent
        - AnswerDelta
        - NarrationDelta
        - ThinkingDelta
        - ToolStarted
        - ToolFinished
        - ToolProgress
        - UsageUpdated
        - CompactionStarted
        - CompactionFinished
        - TurnFinished

## DataFrame enrichment

Add typed columns using each row's supplied content. See the
[job enrichment example](../extraction-and-enrichment.md#example-find-jobs-that-fit).

::: tabulaflow.agents.enrichment.DataFrameEnricher

## Extraction and summarization

These services can be used directly without a chat session. Import
`EntityExtractor` from `tabulaflow.agents.extraction`. Pass a Pydantic model class
to `extract(..., record_type=Place, instruction=...)` to receive a `list[Place]`.

::: tabulaflow.agents.extraction.extractor.EntityExtractor

::: tabulaflow.agents.summarization.DataSourceSummarizer

## Data tools

::: tabulaflow.agents.tools.connect_data_source.ConnectDataSourceTool

::: tabulaflow.agents.tools.run_query.RunQueryTool

::: tabulaflow.agents.tools.run_query.QueryExecution

::: tabulaflow.agents.tools.run_query.LLMParameter

::: tabulaflow.agents.tools.registry.run_query.RegistryRunQueryTool

::: tabulaflow.agents.tools.get_table_schema.GetTableSchemaTool

::: tabulaflow.agents.tools.get_table_schema.TableSchemaExecution

::: tabulaflow.agents.tools.get_column_json_schema.GetColumnJsonSchemaTool

::: tabulaflow.agents.tools.registry.get_schema.RegistryGetSchemaTool

::: tabulaflow.agents.tools.registry.get_table_schema.RegistryGetTableSchemaTool

::: tabulaflow.agents.tools.registry.get_column_json_schema.RegistryGetColumnJsonSchemaTool

::: tabulaflow.agents.tools.registry.get_data_source_document.RegistryGetDataSourceDocumentTool

::: tabulaflow.agents.tools.registry.write_result_table.WriteResultTableTool

## Extraction and enrichment tools

::: tabulaflow.agents.tools.run_subagent_for_each_row.RunSubagentForEachRowTool

::: tabulaflow.agents.tools.extract_rows_from_documents.ExtractRowsFromDocumentsTool

::: tabulaflow.agents.tools.add_canonical_name.AddCanonicalNameTool

## Output tools

::: tabulaflow.agents.tools.create_parameterized_source.CreateParameterizedArtifactSourceTool

::: tabulaflow.agents.tools.create_parameterized_source.CreatedParameterizedArtifactSource

::: tabulaflow.agents.tools.render_chart.RenderChartTool

::: tabulaflow.agents.tools.render_map.RenderMapTool

::: tabulaflow.agents.tools.render_graph.RenderGraphTool

::: tabulaflow.agents.tools.show_artifacts.ShowArtifactsTool

::: tabulaflow.agents.tools.show_artifacts.ArtifactRef

::: tabulaflow.agents.tools.show_artifacts.ArtifactBundle

::: tabulaflow.agents.tools.show_artifacts.Artifacts

## Browser and filesystem tools

::: tabulaflow.agents.tools.browser.tool.WebBrowserTool

::: tabulaflow.agents.tools.browser.manager.WebBrowserManager

::: tabulaflow.agents.tools.filesystem.access.FilesystemRoot

::: tabulaflow.agents.tools.filesystem.view.ViewTool

::: tabulaflow.agents.tools.filesystem.edit.EditFileTool

::: tabulaflow.agents.tools.filesystem.patch.ApplyPatchTool

::: tabulaflow.agents.tools.shell.tool.ExecuteBashTool

::: tabulaflow.agents.tools.shell.tool.BashMode

::: tabulaflow.agents.tools.shell.tool.WaitTimeout

## Usage and traces

::: tabulaflow.agents.trace.Usage

::: tabulaflow.agents.trace.Trajectory

::: tabulaflow.agents.trace.Message

::: tabulaflow.agents.trace.SystemMessage

::: tabulaflow.agents.trace.UserMessage

::: tabulaflow.agents.trace.AssistantMessage

::: tabulaflow.agents.trace.ToolCall

::: tabulaflow.agents.trace.ToolResponse

::: tabulaflow.agents.trace.compute_api_cost

::: tabulaflow.agents.trace.instrument_agents

## Tool metrics

Tool `metrics` properties expose these per-tool counters. Research-specific
counters are documented with the [research tools](../../research-toolkit/api/agents.md#tool-metrics).

::: tabulaflow.agents.tools.protocols.ToolMetrics

::: tabulaflow.agents.tools.protocols.sum_tool_metrics

::: tabulaflow.agents.tools.run_query.RunQueryToolMetrics

::: tabulaflow.agents.tools.get_table_schema.GetTableSchemaToolMetrics

::: tabulaflow.agents.tools.get_column_json_schema.GetColumnJsonSchemaToolMetrics

::: tabulaflow.agents.tools.registry.get_schema.RegistryGetSchemaToolMetrics

::: tabulaflow.agents.tools.registry.get_data_source_document.RegistryGetDataSourceDocumentToolMetrics

::: tabulaflow.agents.tools.browser.tool.WebBrowserToolMetrics

::: tabulaflow.agents.tools.filesystem.view.ViewToolMetrics

::: tabulaflow.agents.tools.filesystem.edit.EditFileToolMetrics

::: tabulaflow.agents.tools.filesystem.patch.ApplyPatchToolMetrics

::: tabulaflow.agents.tools.shell.tool.BashToolMetrics

## Runtime and model configuration

Initialize process-wide policies before creating model or browser resources.
Use `make_agent` to construct a Pydantic AI agent with TabulaFlow's shared
model throttling.

::: tabulaflow.agents.config.AgentRuntimeConfig

::: tabulaflow.agents.config.AgentCacheMode

::: tabulaflow.agents.runtime.initialize_agent_runtime

::: tabulaflow.agents.llm.make_agent

::: tabulaflow.agents.llm.make_model_settings

::: tabulaflow.agents.llm.ReasoningLevel

::: tabulaflow.agents.llm.ReasoningEffort

::: tabulaflow.agents.llm.ServiceTier
    options:
      show_docstring_description: false

::: tabulaflow.agents.llm.model_display_name

::: tabulaflow.agents.llm.embedding_throttle

## Tool contracts

Tools expose a model-facing adapter through `__call__` and
`as_pydantic_ai_tool()`. Tools with an `execute(...)` method also support direct
programmatic use. Registry adapters resolve connector aliases and may return
`ToolReturn` objects carrying display metadata. Check each tool's return type;
the adapters do not all return the same shape.

::: tabulaflow.agents.tools.protocols.AgentTool

::: tabulaflow.agents.tools.protocols.ToolCallOutcome

::: tabulaflow.agents.tools.protocols.ToolProgressUpdate

::: tabulaflow.agents.tools.protocols.ProgressReportingTool

::: tabulaflow.agents.tools.protocols.LLMProfileTool

## Media inputs

These APIs prepare binary values for model input. Core media detection is
documented in the [Core reference](core.md#media-values).

::: tabulaflow.agents.media.to_binary_content

::: tabulaflow.agents.media.select_pdf_pages

::: tabulaflow.agents.media.PdfSelection

::: tabulaflow.agents.media.inspect_inline_media

::: tabulaflow.agents.media.InlineMediaItem

::: tabulaflow.agents.media.InlineMediaCandidate

::: tabulaflow.agents.media.materialize_inline_media

::: tabulaflow.agents.media.UnrecognizedMediaError

::: tabulaflow.agents.media.UnsupportedModelMediaError

## Message storage

`MessageStore` persists user prompts and tool responses in a writable SQL
connector. Scoped stores attach an agent provenance tag to writes.

::: tabulaflow.agents.message_store.MessageStore

::: tabulaflow.agents.message_store.ScopedMessageStore
    options:
      merge_init_into_class: false

::: tabulaflow.agents.message_store.MessageKind
