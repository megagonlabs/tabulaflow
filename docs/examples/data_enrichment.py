# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

# --8<-- [start:example]
import asyncio
from tempfile import TemporaryDirectory

import pandas as pd

from tabulaflow.agents.tools import RunSubagentForEachRowTool
from tabulaflow.data import SQLConnector


async def main():
    with TemporaryDirectory() as directory:
        database = await SQLConnector.from_url_async(f"duckdb:///{directory}/tickets.duckdb", read_only=False)
        result = await database.run_query_async("""
            CREATE TABLE tickets (
                ticket_id INTEGER PRIMARY KEY,
                message TEXT,
                category ENUM ('billing', 'account', 'technical')
            )
        """)
        if result.error is not None:
            raise RuntimeError(result.error.message)
        await database.write_dataframe_async(
            pd.DataFrame(
                {
                    "ticket_id": [101, 102, 103],
                    "message": [
                        "I was charged twice for my last order.",
                        "I cannot sign in after resetting my password.",
                        "The app crashes when I upload a photo.",
                    ],
                }
            ),
            "tickets",
            mode="append",
        )

        enricher = RunSubagentForEachRowTool(database, subagent_llm="openai-responses:gpt-5-mini")
        summary = await enricher.execute(
            schema_name=None,
            table_name="tickets",
            task_query="SELECT ticket_id, message FROM tickets WHERE category IS NULL",
            task_instruction="Classify this support ticket: {{ message }}",
            key_columns=["ticket_id"],
            output_columns=["category"],
        )
        print(summary)

        result = await database.run_query_async("SELECT ticket_id, category FROM tickets ORDER BY ticket_id")
        if result.error is not None:
            raise RuntimeError(result.error.message)
        print(result.df.to_string(index=False))
        await database.close_async()


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
