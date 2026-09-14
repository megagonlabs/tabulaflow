# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector


async def load_sample_data(stock):
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


async def main():
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    try:
        await load_sample_data(stock)
        registry = DataConnectorRegistry()
        registry.register("stock", stock)
        session = ChatSession(registry=registry, model="openai-responses:gpt-5-mini", reasoning="low")
        try:
            result = await session.run("Which products are below their reorder point?")
            print(result.text)

            # The follow-up retains the first turn's context automatically.
            # Stream tool activity and answer text, then read the final usage.
            async for event in session.run_stream("How many units of each should I order to reach those levels?"):
                if event.kind == "tool_started":
                    print("\nTool:", event.name)
                elif event.kind == "answer_delta":
                    print(event.content, end="", flush=True)
                elif event.kind == "turn_finished":
                    print("\nUsage:", event.result.usage)
        finally:
            await session.aclose()
    finally:
        await stock.close_async()


if __name__ == "__main__":
    asyncio.run(main())
