# Agents

Research agents turn benchmark tasks into typed predictions. Choose an agent
compatible with the benchmark's task family, then keep its model and method
configuration explicit in the experiment script.

## Choose an agent

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

Start with `direct_prompting` to measure query generation without tools, or
`full_schema` when the model should execute queries as it works. Use
`schema_linking` or `schema_discovery` to study schema selection on SQL databases.
Direct prompting and full schema also support Cypher with a graph formatter.

Agents declare a task type, output type, and Pydantic configuration class.
`predict_async(...)` checks task-family compatibility before calling the agent's
prediction method. The query family is called `simple` in the API; database
and schema support also depend on the chosen implementation.

## Configure an agent

`BasicAgentConfig` controls shared settings such as the model, schema formatter,
temperature, maximum steps, reasoning effort, and column descriptions.
Specialized configuration models add only method-specific choices:

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

Agent configuration defines the method. Process-wide model limits and
preprocessing caches are configured separately in
[Running experiments](running-experiments.md#configure-concurrency-and-caching).
See the [agent reference](api/agents.md) for method-specific fields.

## Ambiguity-aware agents

ARCS and AMBROSIA-S represent questions with multiple valid interpretations.
The structured agent makes those choices inspectable instead of returning only
one SQL string.

```python title="ambiguity_aware_queries.py"
--8<-- "examples/ambiguity_aware_queries.py"
```

The example predicts finite or open-ended ambiguity points, generates queries
for their interpretations, executes them, and prints readable task reports.
It uses two deterministic AMBROSIA-S tasks; exact interpretations may vary.

After setting `OPENAI_API_KEY`, download AMBROSIA-S and run from a source checkout:

```bash
uv run tabulaflow benchmark download ambrosia-s
uv run python docs/examples/ambiguity_aware_queries.py
```

In an installed project, save the example as `ambiguity_aware_queries.py` and
run `uv run ambiguity_aware_queries.py` instead.

The agent and its user simulator can both make paid model calls. Their usage is
tracked separately in the resulting run.

See [ambiguity evaluation](evaluation.md#evaluate-ambiguity) for intended-query
accuracy, interpretation coverage, and clarification effort.

## dbt transformations

`DbtAgent` works on Spider 2.0 dbt projects and produces transformed tables.
Give `predict_async(...)` a distinct `output_dir` for each run: this is the
agent's working directory for dbt tasks. Evaluate with `Spider2DuckdbMatch`;
the query execution stage does not execute dbt projects.

Next, [run and compare strategies](running-experiments.md#compare-strategies),
or [implement your own agent](extending.md#implement-an-agent).
