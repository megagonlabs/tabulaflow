# Agents

Research strategies operate on benchmark tasks and return typed task outputs.
They are separate from the interactive library's
[`ChatSession`][tabulaflow.agents.chat.session.ChatSession].

## Registry and contracts

A registered strategy declares `name`, `task_type`, `output_type`, and
`config_cls`. It provides `from_config_async(...)` and the `predict_async(...)`
method appropriate for its task family.

```python
from tabulaflow.research.agents import agent_registry

agent_cls = agent_registry.get_class("full_schema")
config = agent_cls.config_cls(max_steps=10)
print(agent_cls.task_type, agent_cls.output_type)
print(config.model_dump())
```

Configuration construction does not call a model. Agent construction and
prediction require credentials for the configured provider.

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
