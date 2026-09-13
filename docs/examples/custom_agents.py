# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

import pandas as pd
from pydantic import BaseModel

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.tools.run_query import RunQueryTool
from tabulaflow.data import SQLConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter


class RestockPlan(BaseModel):
    products: list[str]
    total_units: int


def order_in_packs(shortfall: int, pack_size: int) -> int:
    """Round a stock shortfall up to a whole number of supplier packs.

    Args:
        shortfall: Number of units needed to reach the reorder point.
        pack_size: Number of units in one supplier pack.
    """
    if shortfall < 0 or pack_size < 1:
        raise ValueError("shortfall must be nonnegative and pack_size must be positive")
    return ((shortfall + pack_size - 1) // pack_size) * pack_size


async def main():
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    try:
        await stock.write_dataframe_async(
            pd.DataFrame(
                {
                    "product": ["USB-C dock", "Laptop stand", "HDMI cable"],
                    "on_hand": [3, 18, 4],
                    "reorder_point": [10, 8, 12],
                    "pack_size": [4, 1, 5],
                }
            ),
            "inventory",
        )
        query_tool = RunQueryTool(stock)
        agent = make_agent(
            "openai-responses:gpt-5-mini",
            output_type=RestockPlan,
            instructions=(
                "Plan restocking from the inventory data. Use order_in_packs to round "
                "each shortfall to supplier packs.\n" + SQLDDLSchemaFormatter().format(stock.schema)
            ),
            tools=[query_tool.as_pydantic_ai_tool(), order_in_packs],
        )
        result = await agent.run("Which products need restocking, and how many units should I order in total?")
        print("Products:", result.output.products)
        print("Total units:", result.output.total_units)
        print("Query calls:", query_tool.metrics().num_calls)
    finally:
        await stock.close_async()


if __name__ == "__main__":
    asyncio.run(main())
