# Running experiments

## Save and restore a run

Save predictions to inspect or evaluate them later without rerunning the agent.
Save again after execution or evaluation to update the reports:

```python
from pathlib import Path
from tabulaflow.research.types import NL2QRunResult

result.to_directory("runs/full-schema", eval_metrics_in_summary=["bird_sql_ex"])
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
        └── trajectory/
```

Reports include queries, tabular results, scores, and available trajectories.
To continue execution or evaluation, reload the original benchmark split with
`qids=[task.qid for task in result.tasks]` and the same database snapshot.

## Configure concurrency and caching

Set shared model limits and connector query limits before creating model resources:

```python
from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.data import SQLConnectorConfig
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader

initialize_agent_runtime(AgentRuntimeConfig(
    max_llm_concurrency=16,
    max_llm_requests_per_minute=120,
    preprocessing_cache_mode="read_write",
))
loader = BirdSQLDatasetLoader(connector_config=SQLConnectorConfig(
    max_query_concurrency=4,
    schema_cache_mode="read_write",
    sql_query_cache_mode="off",
))
```

`batch_size` limits concurrent tasks. Runtime limits apply to model requests
across the process; connector limits apply to database queries.

`read_write` reuses cached schemas and preprocessing outputs across runs.
You can also [prepare inputs](api/preprocessing.md#prepare-reusable-inputs), such
as ER diagrams and embeddings, before prediction. Keep cached inputs aligned
with the database snapshot and query caching off when measuring execution time.

See [runtime settings](../python-library/api/agents.md#runtime-and-model-configuration)
and [connector settings](../python-library/api/data.md#configuration) for all
limits and cache policies.

## Ensemble predictions

Combine predictions through majority voting over query results, model selection,
or agent-based selection. Choose an [ensembler](api/pipelines.md#ensembling)
and pass candidate runs for the same benchmark, split, and task QIDs:

```python
from tabulaflow.research.pipelines import ensemble_async

combined = await ensemble_async(ensembler, results, dataset, batch_size=8)
```

The returned run can be executed, evaluated, and saved through the same pipeline.
The ensembler must support the candidates' output family.

## Enable tracing

Set `PHOENIX_COLLECTOR_ENDPOINT` (and `PHOENIX_API_KEY` when required), or
`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`, then enable
instrumentation before constructing agents:

```python
from tabulaflow.research.observability import configure_research_observability

configure_research_observability()
```

Built-in agents group predictions by task QID. Local trajectories are also
available in saved run reports.
