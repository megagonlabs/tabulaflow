# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tabulaflow==0.1.0",
#     "pandas>=2.2.3",
# ]
# ///

import asyncio
import json

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
        read_only=False,
    )
    support = await SQLConnector.from_url_async(
        "sqlite+aiosqlite:///:memory:",
        read_only=False,
    )
    await load_sample_data(sales, support)
    table = sales.schema.tables[0]
    print("Table:", table.name)  # sales
    print("Columns:", [column.name for column in table.columns])
    # ['order_id', 'region', 'revenue_usd']

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

    for artifact in result.output.artifacts:
        if artifact.kind in ("table", "chart"):
            data = await session.output_store.resolve_artifact_source(artifact.source_id)
            print("Artifact:", artifact.label)
            print("Source:", data.metadata.connector_alias)
            print("SQL:", data.metadata.query)
            print("DataFrame:\n", data.df)

            if artifact.kind == "chart":
                print("Vega-Lite:", json.dumps(artifact.spec, indent=2))

    await session.aclose()
    await support.close_async()
    await sales.close_async()


if __name__ == "__main__":
    asyncio.run(main())
