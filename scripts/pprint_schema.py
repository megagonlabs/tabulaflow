import asyncio
import argparse
from dataclasses import dataclass
from mintq.formatters import formatter_registry
from mintq.schema import SQLSchema
from mintq.preprocessors import SchemaCompressor


@dataclass
class SchemaWrapper:
    """Minimal wrapper to satisfy BaseSQLDBConnector protocol for schema-only usage."""
    global_id: str
    schema: SQLSchema


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", default="cache/schemas/spider2-snow+GITHUB_REPOS_DATE.json")
    parser.add_argument("--compress", action="store_true")
    parser.add_argument("--no_description", action="store_true")
    parser.add_argument("--formatter", default="sql_basic")
    args = parser.parse_args()
    print(args)
    print()

    with open(args.input_path, "r") as f:
        schema = SQLSchema.model_validate_json(f.read())

    if args.compress:
        wrapper = SchemaWrapper(global_id=args.input_path, schema=schema)
        schema = await SchemaCompressor().preprocess_async(wrapper)  # type: ignore[arg-type]

    formatter = formatter_registry.get_class(args.formatter)()
    schema_str = formatter.format(schema, add_description=not args.no_description)
    print(schema_str)
    print()
    print(f"(schema length: {len(schema_str)} characters)")


if __name__ == "__main__":
    asyncio.run(main())
