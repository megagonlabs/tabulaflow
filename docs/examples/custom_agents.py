# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3", "httpx>=0.28.1"]
# ///

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pandas as pd
from pydantic import BaseModel
from pydantic_ai import ToolReturn

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.tools import RunQueryTool, ViewTool
from tabulaflow.agents.tools.run_query import LLMParameter
from tabulaflow.data import SQLConnector


class SupportReply(BaseModel):
    message: str
    suggested_steps: list[str]
    references: list[str]
    ticket_id: str | None


async def prepare_example(orders, support_dir):
    await orders.write_dataframe_async(
        pd.DataFrame(
            {
                "order_id": [1001, 1002, 1003, 1004],
                "customer_id": [7, 8, 7, 7],
                "product": ["USB-C dock", "Monitor", "Laptop stand", "USB-C dock"],
                "purchased_on": ["2026-08-18", "2026-08-20", "2026-08-22", "2025-11-05"],
                "status": ["delivered", "shipped", "shipped", "delivered"],
            }
        ),
        "orders",
    )
    bundled = Path(__file__).with_name("support")
    async with httpx.AsyncClient() as client:
        for name in ("faq.txt", "dock-guide.pdf"):
            if bundled.is_dir():
                data = (bundled / name).read_bytes()
            else:
                response = await client.get(f"https://megagonlabs.github.io/tabulaflow/examples/support/{name}")
                response.raise_for_status()
                data = response.content
            (support_dir / name).write_bytes(data)


async def run_support_agent(orders, support_dir, customer_id):
    query_tool = RunQueryTool(orders)
    view = ViewTool(working_dir=support_dir)
    tickets = []

    async def query_order(order_id):
        # The application owns the SQL and customer scope, not the agent.
        return await query_tool.execute(
            "SELECT order_id, product, status FROM orders WHERE order_id = :order_id AND customer_id = :customer_id",
            parameters=[
                LLMParameter(parameter_name="order_id", parameter_value=order_id),
                LLMParameter(parameter_name="customer_id", parameter_value=customer_id),
            ],
        )

    async def find_orders(product: str) -> ToolReturn | str:
        """Find the signed-in customer's orders by product name, newest first."""
        if not product.strip():
            return "(error: product must not be empty)"
        execution = await query_tool.execute(
            "SELECT order_id, product, purchased_on FROM orders "
            "WHERE customer_id = :customer_id AND instr(lower(product), lower(:product)) > 0 "
            "ORDER BY purchased_on DESC, order_id DESC",
            parameters=[
                LLMParameter(parameter_name="customer_id", parameter_value=customer_id),
                LLMParameter(parameter_name="product", parameter_value=product.strip()),
            ],
        )
        return ToolReturn(return_value=execution.output, metadata=execution)

    async def lookup_order(order_id: int) -> ToolReturn:
        """Look up an order belonging to the signed-in customer."""
        execution = await query_order(order_id)
        return ToolReturn(return_value=execution.output, metadata=execution)

    async def open_support_ticket(order_id: int, issue: str) -> str:
        """Record a support ticket for the signed-in customer's order and return its ID."""
        if not issue.strip():
            return "(error: issue must not be empty)"
        # Check ownership even if the agent skipped lookup_order.
        execution = await query_order(order_id)
        result = execution.exec_result
        if result.error is not None:
            return execution.output
        if result.df is None or result.df.empty:
            return "(error: order not found for this customer)"
        ticket_id = f"SUP-{len(tickets) + 1}"
        tickets.append({"ticket_id": ticket_id, "order_id": order_id, "issue": issue.strip()})
        return ticket_id

    agent = make_agent(
        "openai-responses:gpt-5-mini",
        output_type=SupportReply,
        instructions=(
            "You are a customer support agent. Follow faq.txt for support guidance, "
            "and use order search, order lookup, and illustrated guides to help the customer. Cite your sources."
        ),
        tools=[view.as_pydantic_ai_tool(), find_orders, lookup_order, open_support_ticket],
    )
    result = await agent.run(
        "The USB-C dock I bought most recently still won't charge my laptop, and I can't find the order number. "
        "I enabled Laptop charging in Dock settings and reconnected the USB-C cable, "
        "but neither helped. Can you open a support ticket?"
    )
    print("Reply:", result.output.message)
    print("Suggested steps:", result.output.suggested_steps)
    print("References:", result.output.references)
    print("Ticket ID:", result.output.ticket_id)
    print("Stored tickets:", tickets)
    print("Query calls:", query_tool.metrics().num_calls)


async def main():
    with TemporaryDirectory() as directory:
        orders = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        try:
            await prepare_example(orders, Path(directory))
            # Supplied by your application's authenticated session.
            await run_support_agent(orders, directory, customer_id=7)
        finally:
            await orders.close_async()


if __name__ == "__main__":
    asyncio.run(main())
