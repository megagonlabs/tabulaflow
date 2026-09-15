# TabulaFlow

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize, or transform across databases, spreadsheets and other
local files, public datasets, and the web. Like a general-purpose coding agent,
it can also write code, work with files, run shell commands, and browse the web.

[Documentation](https://megagonlabs.github.io/tabulaflow/) |
[Python library](#python-library) | [Research toolkit](#research-toolkit)

## Data agent

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

Work with typed tasks, schemas, and predictions. Saved runs include JSON
results, CSV summaries, and readable task reports with queries, scores, and
agent trajectories. Token usage and latency are tracked for analysis.

[Research toolkit guide](https://megagonlabs.github.io/tabulaflow/research-toolkit/quick-start/)
