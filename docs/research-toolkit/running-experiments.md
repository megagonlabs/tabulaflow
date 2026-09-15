# Running experiments

Compose an experiment in Python, keep its configuration explicit, and save
results between stages. Start with a small, fixed
[task selection](benchmarks.md#select-tasks-reproducibly) and a compatible
[agent](agents.md).

## Run each stage

The [quick start](quick-start.md#example-evaluate-a-full-schema-agent) contains a
complete script. The stages have separate responsibilities:

| Stage | Effect |
| --- | --- |
| `predict_async(...)` | Creates one agent per task and returns an `NL2QRunResult` |
| `execute_async(...)` | Adds missing reference and predicted query results in place |
| `evaluate_async(...)` | Replaces task evaluation metrics and run-level aggregates in place |
| `result.to_directory(...)` | Writes the current run and its reports |

For a loaded `dataset`, a SQL baseline looks like this inside an async function:

```python
from tabulaflow.research.agents import BasicAgentConfig, FullSchemaAgent
from tabulaflow.research.metrics import BirdSQLEx, Executable
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async

result = await predict_async(
    FullSchemaAgent,
    BasicAgentConfig(llm="openai-responses:gpt-5-mini"),
    dataset,
    batch_size=8,
)
await execute_async(result, dataset, batch_size=8, timeout=60)
await evaluate_async(result, dataset, metrics=[BirdSQLEx(), Executable()], batch_size=8)
```

Per-task prediction exceptions are logged and represented by empty outputs so
other predictions can finish. Agent construction and task-contract errors can
raise directly. Execution stores query errors in `ExecResult.error`; evaluation
errors propagate to the caller. See [failure analysis](evaluation.md#inspect-failures)
for distinguishing these cases.

For dbt, prediction prepares and modifies a project under `output_dir`; evaluate
it with `Spider2DuckdbMatch`. The query execution stage has no work for dbt tasks.

## Configure concurrency and caching

Initialize the shared agent runtime before creating model resources. For example:

```python
from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.data import SQLConnectorConfig
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader

initialize_agent_runtime(AgentRuntimeConfig(
    preprocessing_cache_mode="read_write",
    max_llm_concurrency=16,
    max_llm_requests_per_minute=120,
))
loader = BirdSQLDatasetLoader(connector_config=SQLConnectorConfig(
    schema_cache_mode="read_write",
    sql_query_cache_mode="off",
    max_query_concurrency=4,
    query_timeout_seconds=60,
))
```

`batch_size` bounds concurrent task work in each pipeline stage. A task can make
multiple model or database calls: the agent runtime limits model requests across
the process, while connector configuration limits database queries. Embedding
requests have their own runtime limits. These controls work together.

Keep cache policies explicit when comparing methods:

| Cache | Stores | Configured by |
| --- | --- | --- |
| Schema | Introspected database metadata | Connector `schema_cache_mode` |
| SQL query | Execution results | Connector `sql_query_cache_mode` |
| Preprocessing | Derived inputs such as ER diagrams and embeddings | Runtime `preprocessing_cache_mode` |

`off` bypasses a cache, `read_write` reuses entries and stores misses, and
`refresh` recomputes and replaces entries. Schema and preprocessing caches also
support `cache_only`, which requires an existing entry. Cached inputs must match
the database snapshot used for the experiment. Query caching changes what
execution timings measure.

Record the model, agent configuration, task QIDs, cache policies, and TabulaFlow
version alongside published results. The run stores task QIDs and agent
configuration, but does not capture every runtime setting or the package version.
See [runtime configuration](../python-library/api/agents.md#runtime-and-model-configuration)
and [connector configuration](../python-library/api/data.md#configuration) for
all fields and environment-variable settings.

## Prepare reusable inputs

Agents can compute derived inputs during prediction. Precompute them when you
want to separate preparation cost from inference or reuse inputs across runs.
With the persistent preprocessing cache enabled above, prepare ER diagrams for
schema linking before prediction:

```python
from tabulaflow.research.pipelines import preprocess_async
from tabulaflow.research.preprocessing import ERDiagramSynthesizer

preprocessor = ERDiagramSynthesizer()
await preprocess_async(dataset, [preprocessor])
print("Preparation usage:", preprocessor.usage())
```

Preprocessing can make model calls. Cache reuse requires the same inputs and
preprocessor configuration as the consuming agent. The preparation stage fills
caches; it does not replace dataset tasks or globally change connector schemas.
Keep its usage separate when reporting inference cost.

See [Preprocessing](api/preprocessing.md) for schema enrichment, question
embeddings, summaries, and their returned values.

## Save a run

Save after prediction to preserve completed model work, then save again after
execution and evaluation:

```python
result.to_directory(
    "runs/full-schema",
    eval_metrics_in_summary=["bird_sql_ex", "executable"],
)
```

```text
runs/full-schema/
├── result.json
├── result_summary.csv
└── readable/
    └── <qid>/
        ├── task_readable.md
        └── trajectory/        # when the agent recorded a trajectory
```

Query result CSVs are also written when tabular results are available. Calling
`to_directory(...)` again updates the reports at that path. Use distinct paths
for independent experiments. Prediction returns its result after all batches;
it does not automatically checkpoint each batch.

## Continue from a saved run

Restore a run without making model calls or reconnecting to databases:

```python
from pathlib import Path
from tabulaflow.research.types import NL2QRunResult

result = NL2QRunResult.model_validate_json(
    Path("runs/full-schema/result.json").read_text()
)
```

To execute or evaluate it, reconstruct its loader with the original data paths
and credentials, and reload the exact saved QIDs. For the BIRD-SQL example:

```python
import asyncio

loader = BirdSQLDatasetLoader()
dataset = await loader.get_split_async(
    result.split,
    databases=result.databases,
    qids=[task.qid for task in result.tasks],
)
try:
    await execute_async(result, dataset, batch_size=8)
    await evaluate_async(result, dataset, metrics=[BirdSQLEx(), Executable()], batch_size=8)
    result.to_directory("runs/full-schema", eval_metrics_in_summary=["bird_sql_ex", "executable"])
finally:
    await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))
```

Execution fills only missing results by default;
`force=True` reruns queries, including previously failed ones. Evaluation replaces
previous scores, so pass the complete desired metric list. These stages reuse
saved predictions; calling `predict_async(...)` starts fresh inference.

## Compare strategies

Hold the benchmark, split, QIDs, model, and evaluation policy fixed while changing
the method. This example compares direct prompting with schema linking:

```python title="compare_research_agents.py"
--8<-- "examples/compare_research_agents.py"
```

After [installing BIRD-SQL](benchmarks.md#install-benchmark-data) and setting
`OPENAI_API_KEY`, save the example and run `uv run compare_research_agents.py`, or
run `uv run docs/examples/compare_research_agents.py` from a source checkout.
It makes paid model calls and writes one directory per strategy under `runs/`.
Scores and costs can vary between runs.

Use [Evaluation and analysis](evaluation.md) to inspect per-task differences,
accuracy, and usage. To add your own strategy to the comparison, follow
[Extending the toolkit](extending.md#implement-an-agent).

## Ensemble predictions

`ensemble_async(ensembler, results, dataset, batch_size=8)` returns a new run
from compatible candidate runs. Candidates must use the same benchmark, split,
and QIDs, with an output family supported by the ensembler. Majority voting,
model-based selection, agent-based selection, and dbt-specific selection are
available in the [pipeline reference](api/pipelines.md#ensembling).

Execute and evaluate the returned run through the same stages. Individual
ensemble exceptions fall back to the first candidate and increment
`aggregated_inference_metrics["fallback_count"]`.

## Enable tracing

Set `PHOENIX_COLLECTOR_ENDPOINT` (and `PHOENIX_API_KEY` when required), or
`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`, then configure
instrumentation before constructing agents:

```python
from tabulaflow.research.observability import configure_research_observability

configure_research_observability()
```

Built-in agents attach predictions to task-QID spans. Custom agents can use
[`trace_prediction`](api/agents.md#tracing) for the same grouping. Local run
outputs and recorded trajectories remain available without a tracing service.

## Release resources

Once a dataset is loaded, put the experiment inside `try/finally` so its live
connectors close even when a stage raises:

```python
import asyncio

try:
    result = await predict_async(FullSchemaAgent, BasicAgentConfig(), dataset, batch_size=8)
finally:
    await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))
```

Next, choose the [metrics and analyses](evaluation.md) for your experiment.
