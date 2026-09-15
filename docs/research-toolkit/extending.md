# Extending the toolkit

## Implement an agent

`StructuredQueryAgent` generates a typed SQL response. This example compares it
with `DirectPromptAgent` on the same three BIRD-SQL tasks, model, and metrics.

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
--8<-- "examples/custom_research_agent.py"
```

After [installing TabulaFlow and BIRD-SQL](quick-start.md#try-it-yourself) and
setting `OPENAI_API_KEY`, save the example and run:

```bash
uv run custom_research_agent.py
```

From a source checkout, run `uv run docs/examples/custom_research_agent.py`.
The script prints accuracy and executability and saves results under
`runs/direct_prompting/` and `runs/structured_query/`.

Return `pred_query=None` for an intentional abstention. Let unexpected exceptions
propagate so the pipeline logs them and records empty outputs. Use
`extra_pred_info` to retain predictions from before postprocessing.

Pass the class directly to `predict_async(...)`, or call
`agent_registry.register(StructuredQueryAgent)` for name-based lookup. See the
[agent contracts](api/agents.md#registry-and-contracts) for ambiguous and dbt
prediction signatures.

## Add a benchmark

Construct an `NL2QDataset` with unique QIDs and database names matching
`db_connectors`. Run this inside an async function with an existing SQLite file
containing an `orders` table:

```python
from tabulaflow.data import SQLConnector
from tabulaflow.research.agents import BasicAgentConfig, DirectPromptAgent
from tabulaflow.research.metrics import SimpleEx
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async
from tabulaflow.research.types import GoldQuery, NL2QDataset, SimpleNL2QTask

connector = await SQLConnector.from_url_async("sqlite+aiosqlite:///orders.sqlite")
try:
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
    result = await predict_async(DirectPromptAgent, BasicAgentConfig(), dataset, batch_size=1)
    await execute_async(result, dataset, batch_size=1)
    await evaluate_async(result, dataset, metrics=[SimpleEx()], batch_size=1)
finally:
    await connector.close_async()
```

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

A metric declares `name` and `compatible_output_types`, and implements
`compute_async(task, db_connector)`. This diagnostic counts returned rows:

```python
from typing import ClassVar

from tabulaflow.data import DataConnector
from tabulaflow.research.types import NL2QTaskOutput, SimpleNL2QTaskOutput


class ReturnedRows:
    name: ClassVar[str] = "returned_rows"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: DataConnector | None = None
    ) -> int | None:
        if not isinstance(task, SimpleNL2QTaskOutput):
            raise TypeError("ReturnedRows requires a single-query output.")
        query = task.pred_query
        if query is None or query.exec_result is None:
            return None
        result = query.exec_result
        if result.error is not None or result.df is None:
            return None
        return len(result.df)
```

Pass an instance alongside the accuracy metric:

```python
await evaluate_async(result, dataset, metrics=[SimpleEx(), ReturnedRows()], batch_size=8)
```

Zero means an empty result; `None` is excluded from the average. Metrics can also
return a dictionary whose keys become task metric names. Register with
`metric_registry.register(ReturnedRows)` for name-based lookup.

A custom aggregator implements `aggregate(result: NL2QRunResult)` and returns
named run-level values. Pass it in `metric_aggregators`, including
`SimpleAverageAggregator()` if you also want averages. See
[aggregation](evaluation.md#aggregate-scores) and the
[metric contracts](api/metrics.md#registry-and-contracts).
