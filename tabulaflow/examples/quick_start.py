# --8<-- [start:example]
import asyncio

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector
from tabulaflow.output.specs import ChartArtifactSpec, TableArtifactSpec


async def load_sample_data(sales: SQLConnector, support: SQLConnector) -> None:
    await sales.write_dataframe_async(
        pd.DataFrame(
            columns=["order_id", "region", "revenue_usd"],
            data=[
                (1001, "West", 1200),
                (1002, "West", 800),
                (1003, "East", 900),
                (1004, "East", 600),
            ],
        ),
        "sales",
    )
    await support.write_dataframe_async(
        pd.DataFrame(
            columns=["ticket_id", "subject", "priority", "status"],
            data=[
                (201, "Checkout payment failures", "high", "open"),
                (202, "Invoice downloads unavailable", "high", "open"),
                (203, "Profile image upload issue", "low", "open"),
                (204, "Password reset emails delayed", "high", "resolved"),
            ],
        ),
        "support",
    )


async def main() -> None:
    async with DataConnectorRegistry() as registry:
        sales = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        # The registry closes registered connectors when this block exits.
        registry.register("sales", sales)
        support = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        registry.register("support", support)
        await load_sample_data(sales, support)

        async with ChatSession(
            registry=registry,
            model="openai:gpt-5.6-sol",
            reasoning="low",
        ) as session:
            result = await session.run(
                "How does revenue compare across regions, and which high-priority "
                "support tickets are still open? Show revenue as a bar chart "
                "and the tickets in a table."
            )
            print("Answer:", result.text)

            for artifact in result.output.artifacts:
                if isinstance(artifact, (TableArtifactSpec, ChartArtifactSpec)):
                    data = await session.output_store.resolve_artifact_source(artifact.source_id)
                    print("Artifact:", artifact.label)
                    print("Source:", data.metadata.connector_alias)
                    print("SQL:", data.metadata.query)
                    print("DataFrame:\n", data.df)


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
