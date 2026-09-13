# Quick start

Ask one agent about sales and customer support, then get a revenue chart and
a ticket table in one structured response. The example creates its own
in-memory databases; no database server, files, or download is needed.

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
routes each query to the appropriate database; no join or workspace is needed.
The connectors are writable so the helper can load the sample DataFrames.

```python title="quick_start.py"
import asyncio

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector


async def load_sample_data(sales, support):
    await sales.write_dataframe_async(
        pd.DataFrame({
            "order_id": [1001, 1002, 1003, 1004],
            "region": ["West", "West", "East", "East"],
            "revenue_usd": [1200, 800, 900, 600],
        }),
        "sales",
    )
    await support.write_dataframe_async(
        pd.DataFrame({
            "ticket_id": [201, 202, 203, 204],
            "subject": [
                "Checkout payment failures",
                "Invoice downloads unavailable",
                "Profile image upload issue",
                "Password reset emails delayed",
            ],
            "priority": ["high", "high", "low", "high"],
            "status": ["open", "open", "open", "resolved"],
        }),
        "support",
    )


async def main():
    sales = await SQLConnector.from_url_async(
        "sqlite+aiosqlite:///:memory:",
        display_name="sales",
        read_only=False,
    )
    support = await SQLConnector.from_url_async(
        "sqlite+aiosqlite:///:memory:",
        display_name="support",
        read_only=False,
    )
    await load_sample_data(sales, support)
    table = sales.schema.tables[0]
    print("Table:", table.name)
    print("Columns:", [column.name for column in table.columns])

    registry = DataConnectorRegistry()
    registry.register("sales", sales)
    registry.register("support", support)
    session = ChatSession(
        registry=registry,
        model="openai-responses:gpt-5-mini",
        reasoning="low",
    )
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

    await session.aclose()
    await support.close_async()
    await sales.close_async()


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
chart viewer. Closing the connectors releases the in-memory databases.

In long-running applications, use `try/finally` to close sessions and connectors
even when an operation fails; this example closes them only on success.

## Next steps

- [Working with data](working-with-data.md): connect your own sources.
- [Agents API](api/agents.md): explore tools and streaming with `run_stream()`.
- [Output API](api/output.md): define tables, charts, maps, and graphs.
