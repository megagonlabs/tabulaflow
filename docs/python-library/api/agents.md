# Agents

Use `ChatSession` for the reusable conversational runtime, or compose the
individual tools into your own agent.

## Chat sessions

A session runs one turn at a time. `run(...)` returns a `ChatResult`;
`run_stream(...)` yields semantic events and ends with `TurnFinished` on
normal completion. Failures and cancellation propagate as exceptions.
Close the session with `aclose()` and close the connectors owned by your
application separately.

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

## Runtime and model configuration

Initialize process-wide policies before creating model or browser resources.
Use `make_agent` to construct a Pydantic AI agent with TabulaFlow's shared
model throttling.

::: tabulaflow.agents.config.AgentRuntimeConfig

::: tabulaflow.agents.runtime.initialize_agent_runtime

::: tabulaflow.agents.llm.make_agent

::: tabulaflow.agents.llm.make_model_settings

::: tabulaflow.agents.llm.ReasoningLevel

::: tabulaflow.agents.llm.ServiceTier
    options:
      show_docstring_description: false

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

## Data tools

::: tabulaflow.agents.tools.connect_data_source.ConnectDataSourceTool

::: tabulaflow.agents.tools.run_query.RunQueryTool

::: tabulaflow.agents.tools.run_query.QueryExecution

::: tabulaflow.agents.tools.registry.run_query.RegistryRunQueryTool

::: tabulaflow.agents.tools.get_table_schema.GetTableSchemaTool

::: tabulaflow.agents.tools.get_column_json_schema.GetColumnJsonSchemaTool

::: tabulaflow.agents.tools.registry.get_schema.RegistryGetSchemaTool

::: tabulaflow.agents.tools.registry.get_table_schema.RegistryGetTableSchemaTool

::: tabulaflow.agents.tools.registry.get_column_json_schema.RegistryGetColumnJsonSchemaTool

::: tabulaflow.agents.tools.registry.get_data_source_document.RegistryGetDataSourceDocumentTool

::: tabulaflow.agents.tools.registry.write_result_table.WriteResultTableTool

## Output tools

::: tabulaflow.agents.tools.create_parameterized_source.CreateParameterizedArtifactSourceTool

::: tabulaflow.agents.tools.render_chart.RenderChartTool

::: tabulaflow.agents.tools.render_map.RenderMapTool

::: tabulaflow.agents.tools.render_graph.RenderGraphTool

::: tabulaflow.agents.tools.show_artifacts.ShowArtifactsTool

::: tabulaflow.agents.tools.show_artifacts.ArtifactRef

::: tabulaflow.agents.tools.show_artifacts.ArtifactBundle

## Extraction and enrichment

::: tabulaflow.agents.tools.run_subagent_for_each_row.RunSubagentForEachRowTool

::: tabulaflow.agents.tools.extract_rows_from_documents.ExtractRowsFromDocumentsTool

::: tabulaflow.agents.tools.add_canonical_name.AddCanonicalNameTool

::: tabulaflow.agents.extraction.entity.EntityExtractor

::: tabulaflow.agents.summarization.DataSourceSummarizer

## Browser and filesystem tools

::: tabulaflow.agents.tools.browser.tool.WebBrowserTool

::: tabulaflow.agents.tools.filesystem.access.FilesystemRoot

::: tabulaflow.agents.tools.filesystem.view.ViewTool

::: tabulaflow.agents.tools.filesystem.edit.EditFileTool

::: tabulaflow.agents.tools.filesystem.patch.ApplyPatchTool

::: tabulaflow.agents.tools.shell.tool.ExecuteBashTool

## Usage and traces

::: tabulaflow.agents.trace.Usage

::: tabulaflow.agents.trace.Trajectory

::: tabulaflow.agents.trace.instrument_agents
