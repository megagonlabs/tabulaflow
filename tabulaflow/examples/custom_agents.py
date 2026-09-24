# --8<-- [start:example]
import asyncio
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.tools import RunQueryTool, ViewTool
from tabulaflow.data import SQLConnector


async def prepare_example(orders: SQLConnector, support_dir: Path) -> None:
    await orders.write_dataframe_async(
        pd.DataFrame(
            [
                (1001, 7, "USB-C dock", "2026-08-18", "delivered"),
                (1002, 8, "Monitor", "2026-08-20", "shipped"),
                (1003, 7, "Laptop stand", "2026-08-22", "shipped"),
                (1004, 7, "USB-C dock", "2025-11-05", "delivered"),
            ],
            columns=["order_id", "customer_id", "product", "purchased_on", "status"],
        ),
        "orders",
    )
    bundled = files("tabulaflow.examples.support")
    for name in ("faq.txt", "dock-guide.pdf"):
        (support_dir / name).write_bytes(bundled.joinpath(name).read_bytes())


async def run_support_agent(orders: SQLConnector, support_dir: Path) -> None:
    query = RunQueryTool(orders)
    tickets: list[dict[str, str | int]] = []

    async def get_orders() -> str:
        """List the signed-in customer's orders, newest first."""
        result = await query.execute(
            "SELECT order_id, product, purchased_on, status FROM orders "
            "WHERE customer_id = 7 ORDER BY purchased_on DESC"
        )
        return result.output

    async def open_support_ticket(order_id: int, issue: str) -> str:
        """Open a support ticket and return its ID."""
        ticket_id = f"SUP-{len(tickets) + 1}"
        tickets.append({"ticket_id": ticket_id, "order_id": order_id, "issue": issue})
        return ticket_id

    agent = make_agent(
        "openai:gpt-5.6-sol",
        instructions=(
            "You are a customer support agent. Follow faq.txt, consult product guides, "
            "look up the customer's order, and cite the files you use."
        ),
        tools=[
            ViewTool(working_dir=str(support_dir)).as_pydantic_ai_tool(),
            get_orders,
            open_support_ticket,
        ],
    )
    result = await agent.run(
        "My newest USB-C dock still won't charge my laptop. I already enabled Laptop charging "
        "and reconnected the USB-C cable. Please open a support ticket."
    )
    print(result.output)
    print("Tickets:", tickets)


async def main() -> None:
    with TemporaryDirectory() as directory:
        orders = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        async with orders:
            await prepare_example(orders, Path(directory))
            await run_support_agent(orders, Path(directory))


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
