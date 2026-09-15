# Agents and tools

Run built-in research strategies or implement your own against shared task
and output contracts. These APIs support benchmark prediction rather than
[interactive chat][tabulaflow.agents.chat.session.ChatSession].

## Registry and contracts

A registered strategy declares `name`, `task_type`, `output_type`, and
`config_cls`. It provides `from_config_async(...)` and the `predict_async(...)`
method appropriate for its task family.

See [Extending the toolkit](../extending.md#implement-an-agent) for a complete
custom strategy. Construction may prepare model resources; prediction requires
credentials for the configured provider.

::: tabulaflow.research.agents.registry.agent_registry

::: tabulaflow.research.agents.registry.SimpleAgentProtocol

::: tabulaflow.research.agents.registry.AmbigSQLAgentProtocol

::: tabulaflow.research.agents.registry.DbtAgentProtocol

::: tabulaflow.research.agents.utils.BasicAgentConfig

## Simple strategies

| Registry key | Strategy |
| --- | --- |
| `direct_prompting` | Direct query generation |
| `full_schema` | Tool-using agent supplied with the full schema |
| `schema_linking` | Schema linking with optional postprocessing and few-shot examples |
| `schema_discovery` | Discover schema information through tools |

::: tabulaflow.research.agents.direct_prompt.DirectPromptAgent

::: tabulaflow.research.agents.full_schema.FullSchemaAgent

::: tabulaflow.research.agents.schema_linking.SchemaLinkingAgent

::: tabulaflow.research.agents.schema_linking.SchemaLinkingAgentConfig

::: tabulaflow.research.agents.schema_discovery.SchemaDiscoveryAgent

::: tabulaflow.research.agents.schema_discovery.SchemaDiscoveryAgentConfig

## Schema-linking components

These components and context types support the schema-linking strategy's
public linking and postprocessing methods.

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

::: tabulaflow.research.agents.dbt.DbtAgent

::: tabulaflow.research.agents.dbt.DbtAgentConfig

## User simulation

::: tabulaflow.research.agents.user_simulator.UserSimulator

::: tabulaflow.research.agents.user_simulator.UserSimulatorConfig

::: tabulaflow.research.agents.user_simulator.NLAmbigPoint

## Research tools

These tools support benchmark-specific schema inspection, clarification,
termination, and dbt execution. General data, browser, and filesystem tools
are documented in the [library reference](../../python-library/api/agents.md).

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
