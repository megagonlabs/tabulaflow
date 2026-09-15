# Agents and tools

## Registry and contracts

A registered strategy declares `name`, `task_type`, `output_type`, and
`config_cls`. It provides `from_config_async(...)` and the `predict_async(...)`
method appropriate for its task family.

The pipeline creates one agent per task. Pass the class directly to
`predict_async(...)`, or register it with `agent_registry.register(YourAgent)`
for name-based lookup in the current Python process.

Return `pred_query=None` for an intentional abstention in a simple task.
Let unexpected prediction exceptions propagate so the pipeline logs them and
records empty outputs. Use `extra_pred_info` to retain predictions from before
postprocessing. Reference queries remain in task outputs for evaluation;
include only question context and schema in model prompts.

See [Extending the toolkit](../extending.md#implement-an-agent) for an implementation.

::: tabulaflow.research.agents.registry.agent_registry

::: tabulaflow.research.agents.registry.SimpleAgentProtocol

::: tabulaflow.research.agents.registry.AmbigSQLAgentProtocol

::: tabulaflow.research.agents.registry.DbtAgentProtocol

::: tabulaflow.research.agents.utils.BasicAgentConfig

## Simple strategies

Compare built-in methods in [Agents](../agents.md).

::: tabulaflow.research.agents.direct_prompt.DirectPromptAgent

::: tabulaflow.research.agents.full_schema.FullSchemaAgent

::: tabulaflow.research.agents.schema_linking.SchemaLinkingAgent

::: tabulaflow.research.agents.schema_linking.SchemaLinkingAgentConfig

::: tabulaflow.research.agents.schema_discovery.SchemaDiscoveryAgent

::: tabulaflow.research.agents.schema_discovery.SchemaDiscoveryAgentConfig

## Schema-linking components

::: tabulaflow.research.agents.schema_linking.SchemaLinker

::: tabulaflow.research.agents.schema_linking.Postprocessor

::: tabulaflow.research.agents.schema_linking.SchemaLinkingContext

::: tabulaflow.research.agents.utils.TaskRunContext

## Ambiguity-aware strategies

::: tabulaflow.research.agents.ambig_simple.AmbigSimpleSQLAgent

::: tabulaflow.research.agents.ambig_simple.AmbigSimpleSQLAgentConfig

::: tabulaflow.research.agents.ambig_flat.AmbigFlatSQLAgent

::: tabulaflow.research.agents.ambig_flat.AmbigFlatSQLAgentConfig

::: tabulaflow.research.agents.ambig_structured.AmbigStructuredSQLAgent

::: tabulaflow.research.agents.ambig_structured.AmbigStructuredSQLAgentConfig

## dbt strategy

`DbtAgent` works on Spider 2.0 dbt projects and produces transformed tables.
Give `predict_async(...)` a distinct `output_dir` for each run: this is the
agent's working directory for dbt tasks. Evaluate with `Spider2DuckdbMatch`;
the query execution stage does not execute dbt projects.

::: tabulaflow.research.agents.dbt.DbtAgent

::: tabulaflow.research.agents.dbt.DbtAgentConfig

## User simulation

::: tabulaflow.research.agents.user_simulator.UserSimulator

::: tabulaflow.research.agents.user_simulator.UserSimulatorConfig

::: tabulaflow.research.agents.user_simulator.NLAmbigPoint

## Research tools

For general data, browser, and filesystem tools, see the
[library reference](../../python-library/api/agents.md).

::: tabulaflow.research.tools.ask_user.AskUserTool

::: tabulaflow.research.tools.finish.FinishTool

::: tabulaflow.research.tools.get_schema.GetSchemaTool

::: tabulaflow.research.tools.get_column_description.GetColumnDescriptionTool

::: tabulaflow.research.tools.search_keywords.SearchKeywordsTool

::: tabulaflow.research.tools.run_dbt.RunDbtTool

::: tabulaflow.research.tools.run_dbt.DbtCommand

## Tool metrics

::: tabulaflow.research.tools.ask_user.AskUserToolMetrics

::: tabulaflow.research.tools.finish.FinishToolMetrics

::: tabulaflow.research.tools.get_schema.GetSchemaToolMetrics

::: tabulaflow.research.tools.get_column_description.GetColumnDescriptionToolMetrics

::: tabulaflow.research.tools.search_keywords.SearchKeywordsToolMetrics

::: tabulaflow.research.tools.run_dbt.RunDbtToolMetrics

## Tracing

Group model activity by task QID. See
[tracing setup](../running-experiments.md#enable-tracing) for provider settings.

::: tabulaflow.research.observability.configure_research_observability

::: tabulaflow.research.observability.trace_prediction
