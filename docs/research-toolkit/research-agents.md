# Research agents

Research agents turn benchmark tasks into typed predictions. Choose an agent
compatible with the benchmark's task family, then keep its model and method
configuration explicit in the experiment script.

## Choose an agent

| Agent | Task | Approach |
| --- | --- | --- |
| `direct_prompting` | Simple | Generate a query directly from the question and schema |
| `full_schema` | Simple | Give a tool-using agent the complete schema |
| `schema_linking` | Simple | Link relevant schema before query generation |
| `schema_discovery` | Simple | Let the agent discover schema through tools |
| `ambig_simple_sql_agent` | Ambiguous | Resolve and predict the intended query |
| `ambig_flat_sql_agent` | Ambiguous | Produce a flat set of interpretations and queries |
| `ambig_structured_sql_agent` | Ambiguous | Model ambiguity points and interpretation queries |
| `dbt_agent` | dbt | Modify a dbt project to produce the requested tables |

All registered agents declare a task type, output type, and Pydantic
configuration class. `predict_async(...)` rejects incompatible task and agent
families before inference.

## Example: Compare two strategies

This example runs direct prompting and schema linking on the same five
BIRD-SQL tasks with the same model and metrics.

```python title="compare_research_agents.py"
--8<-- "examples/compare_research_agents.py"
```

Each strategy writes a separate run and prints aggregate execution accuracy
and executability. Exact scores and cost vary, but the benchmark selection and
evaluation remain fixed for a fair comparison.

After [downloading BIRD-SQL](benchmarks.md#install-benchmark-data) and setting
`OPENAI_API_KEY`, run from the repository root with:

```bash
uv run python docs/examples/compare_research_agents.py
```

This makes paid model calls and sends questions, relevant schema, and tool
results to the provider.

## Configure an agent

`BasicAgentConfig` controls shared settings such as the model, schema formatter,
temperature, maximum steps, reasoning effort, and column descriptions.
Specialized configuration models add only method-specific choices:

```python
config = SchemaLinkingAgentConfig(
    llm="openai-responses:gpt-5-mini",
    num_few_shot_examples=0,
    do_schema_linking=True,
    do_postprocessing=True,
)
```

Schema-linking and schema-discovery agents can reuse cached schema summaries,
column profiles, predicted foreign keys, question embeddings, and ER diagrams.
Initialize the shared agent runtime with a persistent preprocessing cache when
reusing that work across runs.

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

After downloading AMBROSIA-S, run:

```bash
uv run tabulaflow benchmark download ambrosia-s
uv run python docs/examples/ambiguity_aware_queries.py
```

The agent and its user simulator can both make paid model calls. Their usage is
tracked separately in the resulting run.

## Add an agent

A custom agent declares `name`, `task_type`, `output_type`, and `config_cls`,
provides `from_config_async(...)`, and implements the prediction method for its
task family. Register it when name-based selection is useful, or pass the class
directly to `predict_async(...)`.

See the [agent API](api/agents.md) for the prediction protocols, built-in
strategies, user simulator, and research tools. Next, choose how to
[evaluate their outputs](evaluation.md).
