# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

# --8<-- [start:result-imports]
from tabulaflow.core import ExecResult

# --8<-- [end:result-imports]
# --8<-- [start:data-imports]
import pandas as pd

from tabulaflow.data import SQLConnector

# --8<-- [end:data-imports]
# --8<-- [start:format-imports]
from tabulaflow.output.formatting import SQLDDLSchemaFormatter

# --8<-- [end:format-imports]
from tabulaflow.output.formatting import format_dataframe


async def load_sample_data(stock):
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


async def main():
    # --8<-- [start:connect]
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    # --8<-- [end:connect]
    try:
        await load_sample_data(stock)
        # --8<-- [start:schema]
        print("Tables:", [table.name for table in stock.schema.tables])
        print(SQLDDLSchemaFormatter().format(stock.schema))
        # --8<-- [end:schema]

        # --8<-- [start:query]
        result = await stock.run_query_async(
            "SELECT product, reorder_point - on_hand AS units_to_order "
            "FROM inventory WHERE on_hand < reorder_point ORDER BY product"
        )
        if result.error is not None:
            raise RuntimeError(result.error.message)

        print("DataFrame:\n", result.df)
        # --8<-- [end:query]
        print("As text:\n", format_dataframe(result.df))

        # --8<-- [start:serialize]
        payload = result.model_dump_json()
        restored = ExecResult.model_validate_json(payload)
        print("Restored DataFrame:\n", restored.df)
        # --8<-- [end:serialize]
    finally:
        await stock.close_async()


if __name__ == "__main__":
    asyncio.run(main())
