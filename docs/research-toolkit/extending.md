# Extending the toolkit

## Implement an agent

Bring your prediction method and reuse the benchmark loaders, execution,
metrics, and reports. This agent generates a typed SQL response:

```python title="custom_research_agent.py"
--8<-- "examples/custom_research_agent.py:agent-imports"

--8<-- "examples/custom_research_agent.py:agent"
```

The same pipeline accepts your agent class directly:

```python
--8<-- "examples/custom_research_agent.py:pipeline-imports"

--8<-- "examples/custom_research_agent.py:integration"
```

After [setting up BIRD-SQL and your API key](quick-start.md#try-it-yourself),
run directly:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/custom_research_agent.py
```

The script runs three BIRD-SQL tasks and saves results under `runs/structured_query/`.

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run python docs/examples/custom_research_agent.py
    ```

    This uses your checkout instead of the script's pinned package version.

See the [agent contracts](api/agents.md#registry-and-contracts) for registration
and other task families.

## Use your own dataset

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

For reusable splits, [implement a dataset loader](api/benchmarks.md#implement-a-loader).

## Add a metric

Declare `name` and `compatible_output_types`, then implement `compute_async(...)`.
This diagnostic counts joins in predicted SQL, including CTEs and subqueries:

```python
from typing import ClassVar

from sqlglot import exp, parse_one
from sqlglot.errors import SqlglotError

from tabulaflow.data import DataConnector
from tabulaflow.research.query_analysis import sqlglot_dialect
from tabulaflow.research.types import NL2QTaskOutput, SimpleNL2QTaskOutput


class JoinCount:
    """Count joins in predicted SQL using the database connector's dialect."""

    name: ClassVar[str] = "join_count"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: DataConnector | None = None
    ) -> int | None:
        if not isinstance(task, SimpleNL2QTaskOutput):
            raise TypeError("JoinCount requires a single-query output.")
        if db_connector is None or db_connector.schema.kind != "sql":
            raise TypeError("JoinCount requires a SQL connector.")
        query = task.pred_query
        if query is None:
            return None
        try:
            parsed = parse_one(query.query, read=sqlglot_dialect(db_connector.language))
        except SqlglotError:
            return None
        return sum(1 for _ in parsed.find_all(exp.Join))
```

After executing predictions, pass an instance alongside the accuracy metric:

```python
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines import evaluate_async

await evaluate_async(result, dataset, metrics=[BirdSQLEx(), JoinCount()], batch_size=8)
print("Average joins:", result.aggregated_eval_metrics["join_count"]["avg"])
```

Missing or unparseable predictions return `None` and are excluded from the
average. See the
[metric reference](api/metrics.md#custom-metrics-and-aggregators) for registration
and custom aggregation.
