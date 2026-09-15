# TabulaFlow

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize, or transform across databases, spreadsheets and other
local files, public datasets, and the web. Like a general-purpose coding agent,
it can also write code, work with files, run shell commands, and browse the web.

[Documentation](https://megagonlabs.github.io/tabulaflow/) |
[Python library](#python-library) | [Research toolkit](#research-toolkit)

Requires Python 3.11 or later on macOS or Linux. Install with
[`uv`](https://docs.astral.sh/uv/), set your API key, and launch from your
project directory:

```bash
uv tool install tabulaflow
export OPENAI_API_KEY="your-api-key"
tabulaflow
```

The app includes sample data. Try:

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

The result opens as an interactive chart, with its underlying data and query
available for inspection. Use `/connect` to add your own data.

For web browsing, also install Chromium:

```bash
uv tool run --from playwright playwright install chromium
```

[Data agent guide](https://megagonlabs.github.io/tabulaflow/data-agent/quick-start/)

TabulaFlow 0.1.0 is a public beta. Minor `0.x` releases may contain documented
breaking changes.

## Python library

Build data agents with reusable connectors, tools, and structured outputs.
Use the components independently or combine them in a `ChatSession` to work
across multiple data sources. Connectors and outputs also work without an LLM.

Add TabulaFlow to your Python project:

```bash
uv add tabulaflow
```

With `OPENAI_API_KEY` set, create an in-memory database, ask for a chart, and
inspect the SQL and DataFrame behind it:

```python
import asyncio

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector


async def main():
    sales = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    await sales.write_dataframe_async(
        pd.DataFrame({"region": ["West", "West", "East"], "revenue_usd": [1200, 800, 1500]}),
        "sales",
    )
    registry = DataConnectorRegistry()
    registry.register("sales", sales)
    session = ChatSession(registry=registry, model="openai-responses:gpt-5-mini", reasoning="low")

    result = await session.run("Show total revenue by region as a bar chart.")
    print("Answer:", result.text)
    for artifact in result.output.artifacts:
        if artifact.kind == "chart":
            data = await session.output_store.resolve_artifact_source(artifact.source_id)
            print("SQL:", data.metadata.query)
            print("DataFrame:\n", data.df)

    await session.aclose()
    await sales.close_async()


asyncio.run(main())
```

`result.text` contains the answer; `result.output` contains structured artifact
specifications linked to their source data.

Query data and inspect its structured schema without an API key. This example
creates an in-memory inventory database and finds products to restock:

```python
import asyncio

import pandas as pd

from tabulaflow.data import SQLConnector


async def main():
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    try:
        await stock.write_dataframe_async(
            pd.DataFrame(
                {
                    "product": ["USB-C dock", "Laptop stand", "HDMI cable"],
                    "on_hand": [3, 18, 4],
                    "reorder_point": [10, 8, 12],
                }
            ),
            "inventory",
        )
        for table in stock.schema.tables:
            print("Table:", table.name)
            for column in table.columns:
                print(f"  {column.name}: {column.dtype}, examples={column.examples}")

        result = await stock.run_query_async(
            "SELECT product, reorder_point - on_hand AS units_to_order "
            "FROM inventory WHERE on_hand < reorder_point ORDER BY product"
        )
        if result.error is not None:
            raise RuntimeError(result.error.message)
        print(result.df)
    finally:
        await stock.close_async()


asyncio.run(main())
```

[Python library guide](https://megagonlabs.github.io/tabulaflow/python-library/quick-start/)

## Research toolkit

TabulaFlow Research extends the main Python library for AI researchers working
on text-to-SQL and data agents. Its benchmark loaders, agents, evaluation
metrics, and experiment pipelines support flexible, rapid, and transparent
experiments.

Reuse agent logic across BIRD-SQL, Spider 2.0, Beaver, ARCS, AMBROSIA, and
CypherBench, with managed benchmark setup and metrics adapted from official
evaluation implementations.

With the Python package installed and `OPENAI_API_KEY` set, download BIRD-SQL:

```bash
uv run tabulaflow benchmark download bird-sql
```

Run three tasks concurrently, measure execution accuracy, and save the results:

```python
import asyncio

from tabulaflow.research.agents import BasicAgentConfig, FullSchemaAgent
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async


async def main():
    dataset = await BirdSQLDatasetLoader().get_split_async(
        "dev",
        databases=["california_schools"],
        subsample_size=3,
    )
    try:
        result = await predict_async(FullSchemaAgent, BasicAgentConfig(), dataset, batch_size=3)
        await execute_async(result, dataset, batch_size=3)
        await evaluate_async(result, dataset, metrics=[BirdSQLEx()], batch_size=3)
        print("Execution accuracy:", result.aggregated_eval_metrics["bird_sql_ex"]["avg"])
        result.to_directory("runs/full-schema")
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


asyncio.run(main())
```

Work with typed tasks, schemas, and predictions. Saved runs keep results and
readable reports together:

```text
runs/full-schema/
├── result.json
├── result_summary.csv
└── readable/
    └── <qid>/
        ├── task_readable.md
        └── trajectory/
            └── <trajectory-id>.md
```

Inspect queries, scores, agent trajectories, token usage, and latency without
rerunning the agent.

[Research toolkit guide](https://megagonlabs.github.io/tabulaflow/research-toolkit/quick-start/)
