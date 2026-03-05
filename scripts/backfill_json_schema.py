"""Backfill json_schema for cached SQLSchema files.

Connects to the actual database and samples rows (same method as
build_column_async in sql_conn.py) to infer JSON schemas for columns with
JSON-like types or TEXT columns containing JSON.

Usage:
    # Dry-run (default): report what would change without writing
    uv run scripts/backfill_json_schema.py --dataset spider2-snow

    # Actually write changes
    uv run scripts/backfill_json_schema.py --dataset spider2-snow --write

    # Process specific databases only
    uv run scripts/backfill_json_schema.py --dataset spider2-snow --write --databases GITHUB_REPOS CRYPTO

    # Force re-infer even if json_schema is already set
    uv run scripts/backfill_json_schema.py --dataset spider2-snow --write --force
"""

import argparse
import asyncio
import logging
import os
import sys

import sqlalchemy
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mintq.db_connector.sql_conn import (
    JSON_TYPES,
    TEXT_TYPES,
    ThrottledEngine,
    _JSON_SCHEMA_SAMPLE_SIZE,
)
from mintq.db_connector.utils import infer_json_schema, looks_like_json
from mintq.schema import SQLSchema

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = os.path.join("cache", "schemas")


def _build_snowflake_url(db_name: str) -> str:
    """Build a Snowflake connection URL from environment variables."""
    from urllib.parse import quote_plus

    sf_user = os.environ["SF_USER"]
    sf_password = os.environ["SF_PASSWORD"]
    sf_account = os.environ["SF_ACCOUNT"]
    return f"snowflake://{quote_plus(sf_user)}:{quote_plus(sf_password)}@{sf_account}/{db_name}"


def _build_sqlite_url(dataset: str, db_name: str) -> str:
    """Build a SQLite connection URL for bird-sql or arcs datasets."""
    if dataset == "bird-sql":
        # Default to dev split
        return f"sqlite+aiosqlite:///data/BIRD-SQL/dev_20240627/dev_databases/{db_name}/{db_name}.sqlite"
    elif dataset == "arcs":
        return f"sqlite+aiosqlite:///data/ARCS/databases/sqlite/{db_name}.sqlite"
    else:
        raise ValueError(f"Unknown SQLite dataset: {dataset}")


def _build_mysql_url(dataset: str, db_name: str) -> str:
    """Build a MySQL connection URL for beaver dataset."""
    if dataset == "beaver":
        port = 13306 if db_name == "dw" else 13307
        return f"mysql+asyncmy://root:root@localhost:{port}/{db_name}"
    else:
        raise ValueError(f"Unknown MySQL dataset: {dataset}")


DATASET_ENGINE_TYPE: dict[str, str] = {
    "spider2-snow": "sync",
    "bird-sql": "async",
    "arcs": "async",
    "beaver": "async",
}

DATASET_ENGINE_KWARGS: dict[str, dict] = {
    "spider2-snow": {
        "connect_args": {
            "disable_ocsp_checks": True,
            "client_session_keep_alive": True,
        },
    },
}


def _build_url(dataset: str, db_name: str) -> str:
    if dataset == "spider2-snow":
        return _build_snowflake_url(db_name)
    elif dataset in ("bird-sql", "arcs"):
        return _build_sqlite_url(dataset, db_name)
    elif dataset == "beaver":
        return _build_mysql_url(dataset, db_name)
    else:
        raise ValueError(f"Unknown dataset: {dataset}")


async def backfill_one_db(
    schema: SQLSchema,
    t_eng: ThrottledEngine,
    *,
    force: bool = False,
) -> int:
    """Backfill json_schema for all applicable columns in a schema.

    Uses the same sampling method as build_column_async: queries up to
    _JSON_SCHEMA_SAMPLE_SIZE non-null rows from the actual database.

    Args:
        schema: The SQLSchema loaded from cache (will be modified in-place).
        t_eng: A ThrottledEngine connected to the database.
        force: If True, re-infer json_schema even if already set.

    Returns:
        Number of columns updated.
    """
    updated = 0

    for table in schema.tables:
        for column in table.columns:
            # Skip if already set (unless --force)
            if column.json_schema is not None and not force:
                continue

            dtype = column.dtype
            should_infer = False

            if dtype in JSON_TYPES:
                should_infer = True
            elif dtype in TEXT_TYPES and column.examples and looks_like_json(column.examples):
                should_infer = True

            if not should_infer:
                continue

            # Sample from the actual database — same as build_column_async
            col = sqlalchemy.column(column.name)  # type: ignore
            tbl: sqlalchemy.sql.expression.FromClause = sqlalchemy.table(
                table.name, schema=table.schema_name
            )
            try:
                result = await t_eng.run_query_async(
                    select(col).select_from(tbl).where(col.isnot(None)).limit(_JSON_SCHEMA_SAMPLE_SIZE)
                )
                sample_values = [row[0] for row in result.result]
            except Exception as e:
                logger.warning(
                    "  Failed to sample %s.%s: %s",
                    table.name,
                    column.name,
                    e,
                )
                continue

            if not sample_values:
                continue

            inferred = infer_json_schema(sample_values)
            if inferred is not None:
                old = column.json_schema
                if old != inferred:
                    column.json_schema = inferred
                    updated += 1
                    logger.debug(
                        "  %s.%s: %s",
                        table.name,
                        column.name,
                        "NEW" if old is None else "UPDATED",
                    )

    return updated


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill json_schema in cached SQLSchema files.")
    parser.add_argument(
        "--dataset",
        required=True,
        choices=list(DATASET_ENGINE_TYPE.keys()),
        help="Dataset prefix (determines connection method).",
    )
    parser.add_argument(
        "--databases",
        nargs="+",
        default=None,
        help="Specific database names to process. Default: all cached databases for the dataset.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes to disk. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-infer json_schema even for columns that already have it.",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE_DIR,
        help=f"Path to schema cache directory (default: {DEFAULT_CACHE_DIR}).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-column changes.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    if not os.path.isdir(args.cache_dir):
        logger.error("Cache directory not found: %s", args.cache_dir)
        sys.exit(1)

    # Discover cached schema files for this dataset
    prefix = f"{args.dataset}+"
    all_files = sorted(f for f in os.listdir(args.cache_dir) if f.startswith(prefix) and f.endswith(".json"))

    if args.databases:
        files = [f for f in all_files if f.removeprefix(prefix).removesuffix(".json") in args.databases]
    else:
        files = all_files

    if not files:
        logger.warning("No cached schemas found for dataset '%s'", args.dataset)
        sys.exit(0)

    engine_type = DATASET_ENGINE_TYPE[args.dataset]
    engine_kwargs = DATASET_ENGINE_KWARGS.get(args.dataset, {})

    logger.info(
        "%s mode | dataset=%s | %d database(s) | force=%s",
        "WRITE" if args.write else "DRY-RUN",
        args.dataset,
        len(files),
        args.force,
    )
    logger.info("")

    total_updated = 0
    files_changed = 0

    for filename in files:
        db_name = filename.removeprefix(prefix).removesuffix(".json")
        cache_path = os.path.join(args.cache_dir, filename)

        # Load cached schema
        with open(cache_path, "r", encoding="utf-8") as f:
            schema = SQLSchema.model_validate_json(f.read())

        # Create engine and ThrottledEngine
        url = _build_url(args.dataset, db_name)
        if engine_type == "async":
            engine = create_async_engine(url, pool_size=8, **engine_kwargs)
        else:
            engine = create_engine(url, pool_size=8, **engine_kwargs)  # type: ignore

        db_semaphore = asyncio.Semaphore(8)
        t_eng = ThrottledEngine(engine_type, engine, None, db_semaphore)

        try:
            updated = await backfill_one_db(schema, t_eng, force=args.force)
        finally:
            if engine_type == "async":
                await engine.dispose()  # type: ignore
            else:
                engine.dispose()  # type: ignore

        if updated > 0:
            files_changed += 1
            total_updated += updated
            logger.info("  %s: %d column(s) updated", filename, updated)

            if args.write:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(schema.model_dump_json(indent=2))
        else:
            logger.info("  %s: no changes", filename)

    logger.info("")
    logger.info(
        "Summary: %d column(s) updated across %d file(s) out of %d",
        total_updated,
        files_changed,
        len(files),
    )
    if not args.write and total_updated > 0:
        logger.info("Re-run with --write to apply changes.")


if __name__ == "__main__":
    asyncio.run(main())
