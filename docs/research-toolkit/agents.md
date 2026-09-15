# Agents

| Agent | Task family | Approach |
| --- | --- | --- |
| `direct_prompting` | Query | Generate a query directly from the question and schema |
| `full_schema` | Query | Give a tool-using agent the complete schema |
| `schema_linking` | Query | Link relevant schema before query generation |
| `schema_discovery` | Query | Let the agent discover schema through tools |
| `ambig_simple_sql_agent` | Ambiguous query | Resolve and predict the intended query |
| `ambig_flat_sql_agent` | Ambiguous query | Produce a flat set of interpretations and queries |
| `ambig_structured_sql_agent` | Ambiguous query | Model ambiguity points and interpretation queries |
| `dbt_agent` | Transformation | Modify a dbt project to produce the requested tables |

Schema linking and discovery support SQL databases. Direct prompting and full
schema also support Cypher. `predict_async(...)` checks
[task-family compatibility](quick-start.md#how-an-experiment-fits-together)
before prediction.

## Configure an agent

`BasicAgentConfig` sets the model, schema formatter, temperature, step limit,
reasoning effort, and column descriptions. Method-specific configurations add
options such as schema linking and postprocessing:

```python
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgentConfig

config = SchemaLinkingAgentConfig(
    llm="openai-responses:gpt-5-mini",
    num_few_shot_examples=0,
    do_schema_linking=True,
    do_postprocessing=True,
)
```

For a CypherBench run with `FullSchemaAgent`, select the graph formatter:

```python
from tabulaflow.research.agents import BasicAgentConfig

config = BasicAgentConfig(schema_formatter="cypher")
```

See [runtime configuration](running-experiments.md#configure-concurrency-and-caching)
for concurrency and caching, and the [agent reference](api/agents.md) for all fields.

## Ambiguity-aware agents

This example runs the structured agent on two AMBROSIA-S tasks, executes queries
for their interpretations, and prints task reports:

```python title="ambiguity_aware_queries.py"
--8<-- "examples/ambiguity_aware_queries.py"
```

After setting `OPENAI_API_KEY`, download AMBROSIA-S and run from a source checkout:

```bash
uv run tabulaflow benchmark download ambrosia-s
uv run python docs/examples/ambiguity_aware_queries.py
```

In an installed project, save the example as `ambiguity_aware_queries.py` and
run `uv run ambiguity_aware_queries.py` instead.

Agent and user-simulator usage are tracked separately. See
[ambiguity evaluation](evaluation.md#evaluate-ambiguity) for accuracy, coverage,
and clarification effort.

## dbt transformations

`DbtAgent` works on Spider 2.0 dbt projects and produces transformed tables.
Give `predict_async(...)` a distinct `output_dir` for each run: this is the
agent's working directory for dbt tasks. Evaluate with `Spider2DuckdbMatch`;
the query execution stage does not execute dbt projects.

See [comparing strategies](running-experiments.md#compare-strategies) or
[implementing an agent](extending.md#implement-an-agent).
