# Quick start

Ask one agent about sales and customer support, then get a revenue chart and
a ticket table in one structured response. The example creates its own
sample databases; no database server or download is needed.

## Set up

Use Python 3.11 or later on macOS or Linux. Add TabulaFlow to your project:

=== "uv"

    ```bash
    uv add tabulaflow
    ```

=== "pip"

    ```bash
    pip install tabulaflow
    ```

Working from a source checkout? Run `uv sync` instead.

Set your OpenAI API key. This example makes paid model calls and sends the
questions, schema, and relevant query results to the provider.

```bash
export OPENAI_API_KEY="your-api-key"
```

## Query two sources

Register `sales` and `support`, then ask one question covering both. The agent
routes each query to the appropriate database; no join or writable workspace
is needed. The helper creates the sample data in `quick_start_data/` and resets
the example tables each time you run the script.

```python title="quick_start.py"
import asyncio
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector


def create_sample_databases(directory):
    tables = {
        "sales": {
            "order_id": [1001, 1002, 1003, 1004],
            "region": ["West", "West", "East", "East"],
            "revenue_usd": [1200, 800, 900, 600],
        },
        "support": {
            "ticket_id": [201, 202, 203, 204],
            "subject": [
                "Checkout payment failures",
                "Invoice downloads unavailable",
                "Profile image upload issue",
                "Password reset emails delayed",
            ],
            "priority": ["high", "high", "low", "high"],
            "status": ["open", "open", "open", "resolved"],
        },
    }
    for name, columns in tables.items():
        with closing(sqlite3.connect(directory / f"{name}.sqlite")) as db:
            pd.DataFrame(columns).to_sql(name, db, if_exists="replace", index=False)


async def main():
    directory = Path("quick_start_data").resolve()
    directory.mkdir(exist_ok=True)
    create_sample_databases(directory)

    registry = DataConnectorRegistry()
    try:
        sales = await SQLConnector.from_url_async(
            f"sqlite+aiosqlite:///{directory / 'sales.sqlite'}",
            display_name="sales",
            read_only=True,
        )
        registry.register("sales", sales)

        support = await SQLConnector.from_url_async(
            f"sqlite+aiosqlite:///{directory / 'support.sqlite'}",
            display_name="support",
            read_only=True,
        )
        registry.register("support", support)

        table = sales.schema.tables[0]
        print("Table:", table.name)
        print("Columns:", [column.name for column in table.columns])

        session = ChatSession(
            registry=registry,
            model="openai-responses:gpt-5-mini",
            reasoning="low",
        )
        try:
            result = await session.run(
                "How does revenue compare across regions, and which high-priority "
                "support tickets are still open? Show revenue as a bar chart "
                "and the tickets in a table."
            )
            print("Answer:", result.text)
            print("Data sources:", result.output.sources)
            print("Artifact count:", len(result.output.artifacts))
            for artifact in result.output.artifacts:
                print("Artifact type:", artifact.kind)
                print("Label:", artifact.label)
        finally:
            await session.aclose()
    finally:
        await registry.close_all_async()


if __name__ == "__main__":
    asyncio.run(main())
```

Run `quick_start.py` in your project environment:

=== "uv"

    ```bash
    uv run quick_start.py
    ```

=== "Python"

    ```bash
    python quick_start.py
    ```

## Use the structured output

`result.text` is the written answer. `result.output` is a typed `OutputSpec`,
with source references and separate chart and table artifacts. The print
statements inspect these fields directly, without parsing the answer text.

Expect a chart showing **West: $2,000** and **East: $1,500**, plus a table of
tickets **201** and **202**. Wording, labels, and artifact order may vary.

For a frontend, use [`OutputResolver`](api/output.md#resolving-outputs) with
`session.output_store` to obtain the data and specifications before closing
the session. This script inspects the output structure; it does not launch a
chart viewer. Connections are closed on exit; the sample databases remain
in `quick_start_data/` for you to inspect.

## Next steps

- [Working with data](working-with-data.md): connect your own sources.
- [Agents API](api/agents.md): explore tools and streaming with `run_stream()`.
- [Output API](api/output.md): define tables, charts, maps, and graphs.
