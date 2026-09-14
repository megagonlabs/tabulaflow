# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

import pandas as pd

from tabulaflow.core import ExecResult
from tabulaflow.data import SQLConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter, format_dataframe


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
        # Inspect the structured schema directly, or format it as SQL DDL.
        print("Tables:", [table.name for table in stock.schema.tables])
        print(SQLDDLSchemaFormatter().format(stock.schema))

        result = await stock.run_query_async(
            "SELECT product, reorder_point - on_hand AS units_to_order "
            "FROM inventory WHERE on_hand < reorder_point ORDER BY product"
        )
        if result.error is not None:
            raise RuntimeError(result.error.message)

        print("DataFrame:\n", result.df)
        print("As text:\n", format_dataframe(result.df))

        # The DataFrame is included automatically in the JSON payload.
        payload = result.model_dump_json()
        restored = ExecResult.model_validate_json(payload)
        print("Restored DataFrame:\n", restored.df)
    finally:
        await stock.close_async()


if __name__ == "__main__":
    asyncio.run(main())
