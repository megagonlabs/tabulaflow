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

Implement `compute_async(task, db_connector)` and declare the metric's `name`
and `compatible_output_types`. Pass an instance to `evaluate_async(...)`.
See the [custom metric example](api/metrics.md#example-add-a-metric) for a
complete implementation and aggregation options.
