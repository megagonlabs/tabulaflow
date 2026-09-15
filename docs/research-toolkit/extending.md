# Extending the toolkit

## Implement an agent

Bring your prediction method and reuse the benchmark loaders, execution,
metrics, and reports. This agent generates a typed SQL response:

| Member | Purpose |
| --- | --- |
| `name` | Identifies the method in saved runs |
| `task_type` | Accepted task family: `simple`, `ambig`, or `dbt` |
| `output_type` | Output representation consumed by metrics |
| `config_cls` | Pydantic model for the method's configuration |
| `from_config_async(...)` | Constructs an agent from that configuration |
| `predict_async(...)` | Returns a typed output for one task |

The pipeline creates one agent per task. The model receives the question,
instructions, document, and schema; reference queries remain in the output for
evaluation.

```python title="custom_research_agent.py"
--8<-- "examples/custom_research_agent.py:agent"
```

The same pipeline accepts your agent class directly:

```python
--8<-- "examples/custom_research_agent.py:integration"
```

[Download the full script](../examples/custom_research_agent.py){download}
for imports, dataset loading, and cleanup.
After [installing TabulaFlow and BIRD-SQL](quick-start.md#try-it-yourself) and
setting `OPENAI_API_KEY`, save the example and run:

```bash
uv run custom_research_agent.py
```

From a source checkout, run `uv run docs/examples/custom_research_agent.py`.
The script runs three BIRD-SQL tasks and saves results under `runs/structured_query/`.

Return `pred_query=None` for an intentional abstention. Let unexpected exceptions
propagate so the pipeline logs them and records empty outputs. Use
`extra_pred_info` to retain predictions from before postprocessing.

Pass the class directly to `predict_async(...)`, or call
`agent_registry.register(StructuredQueryAgent)` for name-based lookup. See the
[agent contracts](api/agents.md#registry-and-contracts) for ambiguous and dbt
prediction signatures.

## Add a benchmark

For an existing `connector` to a database containing an `orders` table, create
an `NL2QDataset` and pass it to the same pipeline:

```python
from tabulaflow.research.types import GoldQuery, NL2QDataset, SimpleNL2QTask

dataset = NL2QDataset(
    name="orders",
    split="test",
    tasks=[SimpleNL2QTask(
        qid="order-count",
        db="orders",
        question="How many orders are there?",
        gold_query=GoldQuery(query="SELECT COUNT(*) FROM orders"),
    )],
    db_connectors={"orders": connector},
)
```

Task QIDs must be unique and each task's `db` must match a connector key.
See [Data connectors](../python-library/data-connectors.md) for connection setup.

For reusable splits, implement `DatasetLoaderProtocol`:

- Declare `name`, available `splits`, `default_metrics`, and a
  `BenchmarkInstallation` describing the required local data.
- Implement `get_databases`, `get_tasks_async`, and `get_db_connectors_async`.
- Implement `get_split_async` to select tasks first, then open only the needed
  connectors and return an `NL2QDataset`. Reuse `select_tasks` for QID filtering
  and deterministic sampling, and `selected_databases` to find required databases.

Register the loader with `dataset_registry.register(YourLoader)`. Database
services can also provide a `BenchmarkRuntime` with start, stop, and readiness
callbacks; see the [benchmark reference](api/benchmarks.md). Registrations apply
to the current Python process.

## Add a metric

Implement `compute_async(task, db_connector)` and declare the metric's `name`
and `compatible_output_types`. Pass an instance to `evaluate_async(...)`.
See the [custom metric example](api/metrics.md#example-add-a-metric) for a
complete implementation and aggregation options.
