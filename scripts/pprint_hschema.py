import asyncio
import argparse
from mintq.formatters import HSchemaFormatter
from mintq.schema import HSQLSchema


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", default="cache/hschema/bird-sql+european_football_2.json")
    args = parser.parse_args()
    print(args)
    print()

    with open(args.input_path, "r") as f:
        hschema = HSQLSchema.model_validate_json(f.read())

    formatter = HSchemaFormatter()
    hschema_str = formatter.format(hschema)
    print(hschema_str)


if __name__ == "__main__":
    asyncio.run(main())
