import asyncio
import argparse
import os
from mintq.formatters import SQLDefaultSchemaFormatter
from mintq.schema import SQLSchema


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", default="cache/schemas/bird-sql+european_football_2.json")
    args = parser.parse_args()
    print(args)
    print()

    with open(args.input_path, "r") as f:
        schema = SQLSchema.model_validate_json(f.read())

    formatter = SQLDefaultSchemaFormatter()
    schema_str = formatter.format(schema)
    print(schema_str)


if __name__ == "__main__":
    asyncio.run(main())
