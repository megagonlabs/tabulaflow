import asyncio
import argparse
from mintq.formatters import SQLDefaultSchemaFormatter
from mintq.schema import SQLSchema
from mintq.metadata_synthesizers import SchemaCompressor


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", default="cache/schemas/spider2-snow+GITHUB_REPOS_DATE.json")
    parser.add_argument("--compress", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    with open(args.input_path, "r") as f:
        schema = SQLSchema.model_validate_json(f.read())

    if args.compress:
        schema = await SchemaCompressor().run_async(schema)

    formatter = SQLDefaultSchemaFormatter()
    schema_str = formatter.format(schema)
    print(schema_str)
    print()
    print(f"(schema length: {len(schema_str)} characters)")


if __name__ == "__main__":
    asyncio.run(main())
