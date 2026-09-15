# Extending the toolkit

Implement your method against the toolkit's task and output contracts, then use
the same execution and evaluation stages as a built-in agent. You can also supply
your own benchmark data, task metrics, or aggregation policy.

## Implement an agent

This example implements `StructuredQueryAgent`, which asks a model to return a
typed SQL response. It compares that method with `DirectPromptAgent` on the same
three BIRD-SQL tasks, model, and metrics. The prompts also differ, so this is a
method comparison rather than an isolated test of response formatting.

An agent supplies four class attributes and two methods:

| Member | Purpose |
| --- | --- |
| `name` | Identifies the method in saved runs |
| `task_type` | Accepted task family: `simple`, `ambig`, or `dbt` |
| `output_type` | Output representation consumed by metrics |
| `config_cls` | Pydantic model for the method's configuration |
| `from_config_async(...)` | Constructs an agent from that configuration |
| `predict_async(...)` | Returns a typed output for one task |

The pipeline creates one agent per task. This example supplies only the question,
instructions, document, and database schema to the model. Reference queries stay
in the returned task output for evaluation. Usage, trajectory, and latency are
returned with each prediction so the usual reports and aggregators can use them.

```python title="custom_research_agent.py"
--8<-- "examples/custom_research_agent.py"
```

After [installing TabulaFlow and BIRD-SQL](quick-start.md#try-it-yourself) and
setting `OPENAI_API_KEY`, save the example and run:

```bash
uv run custom_research_agent.py
```

From a source checkout, run `uv run docs/examples/custom_research_agent.py`.
The script makes paid model calls, prints accuracy and executability for each
method, and writes `runs/direct_prompting/` and `runs/structured_query/`.
Scores vary between calls; the example does not claim either method is better.

Replace the prediction logic with your method while keeping the output contract.
Return `pred_query=None` if the method intentionally produces no answer. Let
unexpected exceptions propagate; the prediction pipeline logs them and records
empty outputs. For a repair or postprocessing method, `extra_pred_info` can also
retain the raw prediction for later analysis.

Passing the class directly to `predict_async(...)` requires no registration.
Use `agent_registry.register(StructuredQueryAgent)` when you need name-based
lookup in the same process. Ambiguous and dbt tasks have different prediction
signatures; see the [agent contracts](api/agents.md#registry-and-contracts).

## Add a benchmark

For a small experiment, construct an `NL2QDataset` directly. Each task needs a
unique QID, a database name that resolves in `db_connectors`, and its reference
answer. For example, with an existing SQLite file containing an `orders` table:

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

Run this inside an async function, as in the full example above. To load recurring
splits, implement `DatasetLoaderProtocol`:

- Declare `name`, available `splits`, `default_metrics`, and a
  `BenchmarkInstallation` describing the required local data.
- Implement `get_databases`, `get_tasks_async`, and `get_db_connectors_async`.
- Implement `get_split_async` to select tasks first, then open only the needed
  connectors and return an `NL2QDataset`. Reuse `select_tasks` for QID filtering
  and deterministic sampling, and `selected_databases` to find required databases.

Use `dataset_registry.register(YourLoader)` for name-based lookup in your process.
Registration does not install a plugin in other processes. A database service
can additionally provide a `BenchmarkRuntime` with start, stop, and readiness
callbacks. See the [benchmark reference](api/benchmarks.md) for these contracts.

## Add a metric

A metric declares a unique `name`, its `compatible_output_types`, and an async
`compute_async(task, db_connector)` method. It returns a number, `None`, or a
dictionary of named numbers. Dictionary keys become task metric keys directly.

This diagnostic measures the number of rows returned by a successful query:

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

Zero means a successful empty result; `None` means no measured result and is
excluded from the default average. Use `metric_registry.register(ReturnedRows)`
only when you need name-based lookup.

A custom aggregator implements `aggregate(result: NL2QRunResult)` and returns a
dictionary of run-level values. Pass it in `metric_aggregators` to replace the
default aggregation list, or include `SimpleAverageAggregator()` to retain the
usual averages. See [Evaluation and analysis](evaluation.md#aggregate-scores)
and the [metric contracts](api/metrics.md#registry-and-contracts).
