# Agents

| Agent | Task | Approach |
| --- | --- | --- |
| `DirectPromptAgent` | Query | Generate a query directly from the question and schema |
| `FullSchemaAgent` | Query | Give a tool-using agent the complete schema |
| `SchemaLinkingAgent` | Query | Link relevant schema before query generation |
| `SchemaDiscoveryAgent` | Query | Let the agent discover schema through tools |
| `AmbigSimpleSQLAgent` | Ambiguous query | Resolve and predict the intended query |
| `AmbigFlatSQLAgent` | Ambiguous query | Produce a flat set of interpretations and queries |
| `AmbigStructuredSQLAgent` | Ambiguous query | Model ambiguity points and interpretation queries |
| [`DbtAgent`](api/agents.md#dbt-strategy) | Transformation | Modify a dbt project to produce the requested tables |

Schema linking and discovery support SQL databases. Direct prompting and full
schema also support Cypher.

## Configure an agent

```python
from tabulaflow.research.agents import BasicAgentConfig, FullSchemaAgent

agent = FullSchemaAgent(
    BasicAgentConfig(
        llm="openai-responses:gpt-4.1",
        max_steps=10,
    )
)
```

Schema formatting is selected automatically. See the [agent reference](api/agents.md)
for all configuration options.

## Ambiguity-aware agents

The structured agent identifies ambiguity points and generates queries for their
interpretations. This example uses `gpt-4.1` on ARCS task `001-5`:

> Report the total revenue for each nation in 1995.

```python
--8<-- "examples/ambiguity_aware_queries.py:prediction"
```

??? result "Example result · ARCS 001-5"

    Recorded · test split · gpt-4.1 · 2025-11-21

    ```text
    --8<-- "examples/results/ambiguity.txt"
    ```

    [Recorded data](../examples/results/recorded-results.json)

After [setting up ARCS](benchmarks.md#arcs) and setting
`OPENAI_API_KEY`, run directly:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/ambiguity_aware_queries.py
```

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run python docs/examples/ambiguity_aware_queries.py
    ```

    This uses your checkout instead of the script's pinned package version.

See [ambiguity evaluation](evaluation.md#evaluate-ambiguity) for accuracy, coverage,
and clarification metrics.
