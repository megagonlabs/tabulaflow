import asyncio

# --8<-- [start:session-imports]
from tabulaflow.agents import ChatSession

# --8<-- [end:session-imports]
# --8<-- [start:data-imports]
import pandas as pd

from tabulaflow.data import DataConnectorRegistry, SQLConnector
# --8<-- [end:data-imports]


async def load_sample_data(stock: SQLConnector) -> None:
    # --8<-- [start:sample-data]
    await stock.write_dataframe_async(
        pd.DataFrame(
            columns=["product", "on_hand", "reorder_point"],
            data=[
                ("USB-C dock", 3, 10),
                ("Laptop stand", 18, 8),
                ("HDMI cable", 4, 12),
            ],
        ),
        "inventory",
    )
    # --8<-- [end:sample-data]


async def main() -> None:
    # --8<-- [start:connect]
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    # --8<-- [end:connect]
    # --8<-- [start:registry]
    registry = DataConnectorRegistry()
    # Make the connector available to the session.
    registry.register("stock", stock)
    # --8<-- [end:registry]
    async with registry:
        await load_sample_data(stock)
        # --8<-- [start:session]
        session = ChatSession(registry=registry, model="openai-responses:gpt-5-mini", reasoning="low")
        # --8<-- [end:session]
        async with session:
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
                    result = event.result
            # --8<-- [end:stream]

            # --8<-- [start:usage]
            usage = result.usage
            if usage is not None:
                print("\nRequests:", usage.api_requests)
                print("Input tokens:", usage.input_tokens)
                print("Output tokens:", usage.output_tokens)
                print(f"Estimated cost: ${usage.api_cost_usd:.6f}")
            # --8<-- [end:usage]

            # --8<-- [start:reset]
            session.reset_conversation()
            # --8<-- [end:reset]


if __name__ == "__main__":
    asyncio.run(main())
