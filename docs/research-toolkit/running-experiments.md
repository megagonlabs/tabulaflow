# Running experiments

| Stage | Effect |
| --- | --- |
| `predict_async(...)` | Creates one agent per task and returns an `NL2QRunResult` |
| `execute_async(...)` | Adds missing reference and predicted query results in place |
| `evaluate_async(...)` | Replaces task evaluation metrics and run-level aggregates in place |
| `result.to_directory(...)` | Writes the current run and its reports |

The [quick start](quick-start.md#example-evaluate-a-full-schema-agent) covers
prediction, execution, and evaluation.

Prediction exceptions are logged and recorded as empty outputs. Construction,
task-contract, and evaluation errors propagate. Query errors appear in
`ExecResult.error`; see [failure analysis](evaluation.md#inspect-failures).
For project-based tasks, see the [dbt strategy](api/agents.md#dbt-strategy).

## Compare strategies

Compare direct prompting and schema linking on the same tasks and model:

```python
--8<-- "examples/compare_research_agents.py:strategies"

--8<-- "examples/compare_research_agents.py:comparison"
```

The [full script](https://github.com/megagonlabs/tabulaflow/blob/main/docs/examples/compare_research_agents.py) loads five BIRD-SQL
tasks and prints a comparison table with accuracy,
executability, token usage, estimated cost, and average task latency. Scores are
fractions from 0 to 1; usage reflects the work performed in that run, including
any preprocessing cache misses.

After [setting up BIRD-SQL and your API key](quick-start.md#try-it-yourself),
run directly:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/compare_research_agents.py
```

Each method's predictions and reports are saved under `runs/<agent>/`.

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run python docs/examples/compare_research_agents.py
    ```

    This uses your checkout instead of the script's pinned package version.

See [paired analysis](evaluation.md#inspect-failures) and
[adding your own strategy](extending.md#implement-an-agent).

## Configure concurrency and caching

Initialize the agent runtime before creating model resources:

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

`batch_size` limits concurrent tasks. The agent runtime limits model requests
across the process; connectors limit database queries. Embedding requests have
separate runtime limits.

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

Runs store task QIDs and agent configuration. For reproducible experiments,
set the schema formatter explicitly, pin the TabulaFlow version, and record
runtime settings separately.
See [runtime configuration](../python-library/api/agents.md#runtime-and-model-configuration)
and [connector configuration](../python-library/api/data.md#configuration) for
all fields and environment-variable settings.

## Prepare reusable inputs

With preprocessing caching enabled, prepare ER diagrams before prediction to
reuse them across runs:

```python
from tabulaflow.research.pipelines import preprocess_async
from tabulaflow.research.preprocessing import ERDiagramSynthesizer

preprocessor = ERDiagramSynthesizer()
await preprocess_async(dataset, [preprocessor])
print("Preparation usage:", preprocessor.usage())
```

This stage fills caches for agents using the same inputs and preprocessor
configuration. Preprocessing can make model calls; report its usage separately
from inference.

See [Preprocessing](api/preprocessing.md) for schema enrichment, question
embeddings, summaries, and their returned values.

## Save and restore a run

Save after prediction to preserve model work, then update the reports after
execution and evaluation. Restore the typed result from the same directory:

```python
from pathlib import Path
from tabulaflow.research.types import NL2QRunResult

result.to_directory("runs/full-schema", eval_metrics_in_summary=["bird_sql_ex", "executable"])
result = NL2QRunResult.model_validate_json(
    Path("runs/full-schema/result.json").read_text()
)
```

```text
runs/full-schema/
├── result.json
├── result_summary.csv
└── readable/
    └── <qid>/
        ├── task_readable.md
        └── trajectory/        # when recorded by the agent
```

Tabular query results are also exported as CSVs. Reusing a directory updates its
reports. Prediction returns after all batches; it does not checkpoint each batch.

To continue execution or evaluation, reload `result.split` with the original
loader and `qids=[task.qid for task in result.tasks]`. Use the same database
snapshot, paths, and credentials. Execution fills missing results; `force=True`
reruns queries. Evaluation replaces scores, so pass the complete metric list.
Calling `predict_async(...)` starts fresh inference.

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

Built-in agents group predictions by task QID. Custom agents can use
[`trace_prediction`](api/agents.md#tracing). Local trajectories do not require
a tracing service.

## Release resources

Close every connector in `dataset.db_connectors` in a `finally` block, as in
the [quick start](quick-start.md#example-evaluate-a-full-schema-agent).
