# --8<-- [start:example]
import asyncio
import json

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector
from tabulaflow.output.specs import ChartArtifactSpec, TableArtifactSpec


async def load_sample_data(sales: SQLConnector, support: SQLConnector) -> None:
    await sales.write_dataframe_async(
        pd.DataFrame(
            columns=["order_id", "customer_id", "revenue_usd"],
            data=[
                (1001, 101, 1200),
                (1002, 101, 800),
                (1003, 102, 900),
                (1004, 103, 600),
            ],
        ),
        "sales",
    )
    await support.write_dataframe_async(
        pd.DataFrame(
            columns=["ticket_id", "customer_id", "subject", "priority", "status"],
            data=[
                (201, 101, "Checkout payment failures", "high", "open"),
                (202, 102, "Invoice downloads unavailable", "high", "open"),
                (203, 103, "Profile image upload issue", "low", "open"),
                (204, 101, "Password reset emails delayed", "high", "resolved"),
            ],
        ),
        "support",
    )


async def main() -> None:
    async with DataConnectorRegistry() as registry:
        sales = await SQLConnector.from_url_async("sqlite:///:memory:", read_only=False)
        # The registry closes registered connectors when this block exits.
        registry.register("sales", sales)
        support = await SQLConnector.from_url_async("sqlite:///:memory:", read_only=False)
        registry.register("support", support)
        workspace = await SQLConnector.from_url_async("duckdb:///:memory:", read_only=False)
        registry.register("workspace", workspace)
        await load_sample_data(sales, support)

        async with ChatSession(
            registry=registry,
            workspace=workspace,
            model="openai:gpt-5.6-sol",
            reasoning="low",
        ) as session:
            result = await session.run(
                "Join sales and support by customer ID. For each customer, show "
                "total revenue and the number of open high-priority tickets. Return "
                "the summary as a table and show total revenue as a bar chart."
            )
            print("Answer:", result.text)

            for artifact in result.output.artifacts:
                if isinstance(artifact, (TableArtifactSpec, ChartArtifactSpec)):
                    data = await session.output_store.resolve_artifact_source(artifact.source_id)
                    print("\n" + "-" * 72)
                    print("Artifact:", artifact.label)
                    print("Source:", data.metadata.connector_alias)
                    print("SQL:", data.metadata.query)
                    print("DataFrame:\n", data.df)
                    if isinstance(artifact, ChartArtifactSpec):
                        print("Vega-Lite spec:")
                        print(json.dumps(artifact.spec, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
