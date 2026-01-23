import asyncio
import argparse
from mintq.formatters import formatter_registry
from mintq.schema import SQLSchema
from mintq.metadata_synthesizers import SchemaCompressor


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", default="cache/schemas/spider2-snow+GITHUB_REPOS_DATE.json")
    parser.add_argument("--compress", action="store_true")
    parser.add_argument("--no_description", action="store_true")
    parser.add_argument("--formatter", default="sql_default")
    args = parser.parse_args()
    print(args)
    print()

    with open(args.input_path, "r") as f:
        schema = SQLSchema.model_validate_json(f.read())

    if args.compress:
        schema = await SchemaCompressor().run_async(schema)

    formatter = formatter_registry.get_class(args.formatter)()
    schema_str = formatter.format(schema, add_description=not args.no_description)
    print(schema_str)
    print()
    print(f"(schema length: {len(schema_str)} characters)")


if __name__ == "__main__":
    asyncio.run(main())
