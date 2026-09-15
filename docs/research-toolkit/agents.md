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
reasoning effort, and column descriptions. The
[comparison example](running-experiments.md#compare-strategies) shows
method-specific settings for schema linking and postprocessing.

For CypherBench, pass `BasicAgentConfig(schema_formatter="cypher")` to
`FullSchemaAgent` or `DirectPromptAgent`.

See [runtime configuration](running-experiments.md#configure-concurrency-and-caching)
for concurrency and caching, and the [agent reference](api/agents.md) for all fields.

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

[Download the full script](../examples/ambiguity_aware_queries.py){download}
to load this task, generate and execute its intended query, evaluate it, and
print the report. After [setting up ARCS](benchmarks.md#install-benchmark-data)
and setting `OPENAI_API_KEY`, run:

```bash
uv run ambiguity_aware_queries.py
```

From a checkout, use `uv run docs/examples/ambiguity_aware_queries.py`.

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
