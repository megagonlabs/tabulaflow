# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tabulaflow==0.1.0",
#     "pandas>=2.2.3",
# ]
# ///

import asyncio
from contextlib import AsyncExitStack
import json

# --8<-- [start:sample-imports]
import pandas as pd
from tabulaflow.data import SQLConnector
# --8<-- [end:sample-imports]

# --8<-- [start:session-imports]
from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry
# --8<-- [end:session-imports]

# --8<-- [start:output-imports]
from tabulaflow.output.resolver import OutputResolver, ResolvedChartArtifact, ResolvedTableArtifact, UnavailableArtifact
# --8<-- [end:output-imports]


# --8<-- [start:sample-data]
async def load_sample_data(sales, support):
    await sales.write_dataframe_async(
        pd.DataFrame(
            {
                "order_id": [1001, 1002, 1003, 1004],
                "region": ["West", "West", "East", "East"],
                "revenue_usd": [1200, 800, 900, 600],
            }
        ),
        "sales",
    )
    await support.write_dataframe_async(
        pd.DataFrame(
            {
                "ticket_id": [201, 202, 203, 204],
                "subject": [
                    "Checkout payment failures",
                    "Invoice downloads unavailable",
                    "Profile image upload issue",
                    "Password reset emails delayed",
                ],
                "priority": ["high", "high", "low", "high"],
                "status": ["open", "open", "open", "resolved"],
            }
        ),
        "support",
    )


# --8<-- [end:sample-data]


async def inspect_outputs(session, result):
    # --8<-- [start:resolve-output]
    resolved = await OutputResolver(session.output_store).resolve(result.output)
    for artifact in resolved.artifacts:
        if isinstance(artifact, UnavailableArtifact):
            print("Unavailable:", artifact.artifact_id, artifact.reason)
        elif isinstance(artifact, (ResolvedTableArtifact, ResolvedChartArtifact)):
            print("Artifact:", artifact.label)
            print("Source:", artifact.result.metadata.connector_alias)
            print("SQL:", artifact.result.metadata.query)
            print("DataFrame:\n", artifact.result.df)
    # --8<-- [end:resolve-output]

    for artifact in resolved.artifacts:
        if isinstance(artifact, ResolvedChartArtifact):
            print("Vega-Lite:", json.dumps(artifact.spec, indent=2))


async def main():
    async with AsyncExitStack() as stack:
        # --8<-- [start:sales-connection]
        sales = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        # --8<-- [end:sales-connection]
        stack.push_async_callback(sales.close_async)
        # --8<-- [start:support-connection]
        support = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        # --8<-- [end:support-connection]
        stack.push_async_callback(support.close_async)
        # --8<-- [start:load-data]
        await load_sample_data(sales, support)
        # --8<-- [end:load-data]

        # --8<-- [start:session]
        registry = DataConnectorRegistry()
        registry.register("sales", sales)
        registry.register("support", support)
        session = ChatSession(
            registry=registry,
            model="openai-responses:gpt-5-mini",
            reasoning="low",
        )
        # --8<-- [end:session]
        stack.push_async_callback(session.aclose)
        # --8<-- [start:question]
        result = await session.run(
            "How does revenue compare across regions, and which high-priority "
            "support tickets are still open? Show revenue as a bar chart "
            "and the tickets in a table."
        )
        print("Answer:", result.text)
        print("Artifacts:", [artifact.label for artifact in result.output.artifacts])
        # --8<-- [end:question]
        await inspect_outputs(session, result)


if __name__ == "__main__":
    asyncio.run(main())
