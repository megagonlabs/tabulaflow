# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

# --8<-- [start:session-imports]
from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry

# --8<-- [end:session-imports]
# --8<-- [start:data-imports]
import pandas as pd

from tabulaflow.data import SQLConnector
# --8<-- [end:data-imports]


async def load_sample_data(stock):
    # --8<-- [start:sample-data]
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
    # --8<-- [end:sample-data]


async def main():
    # --8<-- [start:connect]
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    # --8<-- [end:connect]
    try:
        await load_sample_data(stock)
        # --8<-- [start:session]
        registry = DataConnectorRegistry()
        registry.register("stock", stock)
        session = ChatSession(registry=registry, model="openai-responses:gpt-5-mini", reasoning="low")
        # --8<-- [end:session]
        try:
            # --8<-- [start:first-turn]
            result = await session.run("Which products are below their reorder point?")
            print(result.text)
            # --8<-- [end:first-turn]

            # --8<-- [start:stream]
            async for event in session.run_stream("How many units of each should I order to reach those levels?"):
                if event.kind == "tool_started":
                    print("\nTool:", event.name)
                elif event.kind == "answer_delta":
                    print(event.content, end="", flush=True)
                elif event.kind == "turn_finished":
                    print("\nUsage:", event.result.usage)
            # --8<-- [end:stream]
            # --8<-- [start:reset]
            session.reset_conversation()
            # --8<-- [end:reset]
        finally:
            await session.aclose()
    finally:
        await stock.close_async()


if __name__ == "__main__":
    asyncio.run(main())
