import argparse
import asyncio
import time
from typing import Any, Literal, cast

from tabulate import tabulate

from tabulaflow.data import Neo4jConnectorConfig, SQLConnectorConfig, SQLConnectorProtocol
from tabulaflow.research.benchmarks import dataset_registry
from tabulaflow.research.preprocessing.schema import SchemaPreprocessor
from tabulaflow.research.reporting import dict_to_df
from tabulaflow.research.types import AmbigNL2QTask, NL2QDataset

MAX_DATABASES_TO_PRINT = 12
AMBIGUITY_TYPES = (
    "semantic_column",
    "semantic_table",
    "semantic_value",
    "semantic_computation",
    "syntactic_column",
    "syntactic_table",
    "syntactic_value",
    "syntactic_computation",
)


def print_nested_counts(title: str, counts: dict[str, dict[str, Any]], table_format: str) -> None:
    print()
    print(f"### {title}")
    print()
    print(
        tabulate(
            dict_to_df(counts, total_column_only=len(counts) > MAX_DATABASES_TO_PRINT),
            headers="keys",
            tablefmt=table_format,
        )
    )


def print_ambiguity_stats(tasks: list[AmbigNL2QTask], databases: list[str], table_format: str) -> None:
    type_counts: dict[str, dict[str, int]] = {
        database: {ambiguity_type: 0 for ambiguity_type in AMBIGUITY_TYPES} for database in databases
    }
    for task in tasks:
        for ambiguity_type in {point.ambiguity_type for point in task.gold_ambiguity_points}:
            type_counts[task.db][ambiguity_type] += 1
    print_nested_counts("Ambiguity Types", type_counts, table_format)

    max_points = max(len(task.gold_ambiguity_points) for task in tasks)
    point_counts: dict[str, dict[str, int]] = {
        database: {str(count): 0 for count in range(1, max_points + 1)} for database in databases
    }
    for task in tasks:
        point_counts[task.db][str(len(task.gold_ambiguity_points))] += 1
    print_nested_counts("Ambiguity Points per Task", point_counts, table_format)

    parameter_counts: dict[str, dict[str, int]] = {
        database: {dtype: 0 for dtype in ("int", "float", "str")} for database in databases
    }
    for task in tasks:
        for point in task.gold_ambiguity_points:
            if point.type == "infinite":
                parameter_counts[task.db][point.parameter_dtype] += 1
    print_nested_counts("Infinite Parameter Types", parameter_counts, table_format)

    query_counts = sorted({len(task.gold_queries) for task in tasks})
    interpretation_counts: dict[str, dict[str, int]] = {
        database: {str(count): 0 for count in query_counts} for database in databases
    }
    for task in tasks:
        interpretation_counts[task.db][str(len(task.gold_queries))] += 1
    print_nested_counts("Interpretation Combinations", interpretation_counts, table_format)

    finite_counts = [sum(point.type == "finite" for point in task.gold_ambiguity_points) for task in tasks]
    infinite_counts = [sum(point.type == "infinite" for point in task.gold_ambiguity_points) for task in tasks]
    total_counts = [len(task.gold_ambiguity_points) for task in tasks]
    interpretation_totals = [len(task.gold_queries) for task in tasks]
    rows: list[tuple[str, int | float]] = []
    for name, values in (
        ("ambiguity_points", total_counts),
        ("finite_ambiguity_points", finite_counts),
        ("infinite_ambiguity_points", infinite_counts),
        ("interpretation_combinations", interpretation_totals),
    ):
        rows.extend(
            ((f"min_{name}", min(values)), (f"avg_{name}", sum(values) / len(values)), (f"max_{name}", max(values)))
        )
    print()
    print("### Aggregated Ambiguity Statistics")
    print()
    print(tabulate(rows, headers=("key", "value"), tablefmt=table_format, floatfmt=".2f"))


def print_basic_stats(dataset: NL2QDataset, table_format: str) -> None:
    rows: list[list[Any]] = []
    for database in sorted(dataset.db_connectors):
        schema = dataset.db_connectors[database].schema
        table_rows = [table.num_rows for table in schema.tables if table.num_rows is not None]
        column_count = sum(len(table.columns) for table in schema.tables)
        described_columns = sum(column.description is not None for table in schema.tables for column in table.columns)
        rows.append(
            [
                database,
                len(schema.tables),
                sum(table_rows),
                max(table_rows, default=0),
                column_count,
                described_columns / column_count if column_count else 0.0,
            ]
        )

    if len(rows) <= MAX_DATABASES_TO_PRINT:
        print("### Per-Database Statistics")
        print()
        print(
            tabulate(
                rows,
                headers=("database", "tables", "total_rows", "max_rows_per_table", "columns", "described_ratio"),
                tablefmt=table_format,
                floatfmt=".2f",
            )
        )

    tables = [row[1] for row in rows]
    total_rows = [row[2] for row in rows]
    max_rows = [row[3] for row in rows]
    columns = [row[4] for row in rows]
    description_ratios = [row[5] for row in rows]
    if not sum(tables):
        raise ValueError("Dataset schemas contain no tables")
    summary = [
        ("dataset", dataset.name),
        ("split", dataset.split),
        ("total_tasks", len(dataset.tasks)),
        ("total_databases", len(rows)),
        ("max_tables_per_db", max(tables)),
        ("avg_tables_per_db", sum(tables) / len(tables)),
        ("min_tables_per_db", min(tables)),
        ("max_rows_per_db", max(total_rows)),
        ("avg_rows_per_db", sum(total_rows) / len(total_rows)),
        ("min_rows_per_db", min(total_rows)),
        ("max_max_rows_per_table", max(max_rows)),
        ("avg_max_rows_per_table", sum(max_rows) / len(max_rows)),
        ("min_max_rows_per_table", min(max_rows)),
        ("max_columns_per_db", max(columns)),
        ("avg_columns_per_db", sum(columns) / len(columns)),
        ("min_columns_per_db", min(columns)),
        ("avg_columns_per_table", sum(columns) / sum(tables)),
        ("avg_ratio_columns_with_desc", sum(description_ratios) / len(description_ratios)),
    ]
    print()
    print("### Dataset Summary")
    print()
    print(tabulate(summary, headers=("key", "value"), tablefmt=table_format, floatfmt=".2f"))


async def print_preprocessed_schema_stats(dataset: NL2QDataset, table_format: str) -> None:
    preprocessor = SchemaPreprocessor()
    rows: list[list[Any]] = []
    for database in sorted(dataset.db_connectors):
        connector = dataset.db_connectors[database]
        schema = connector.schema
        sql_connector = cast(SQLConnectorProtocol, connector)
        processed = await preprocessor.preprocess_async(sql_connector)
        rows.append(
            [
                database,
                sum(len(table.columns) for table in schema.tables),
                sum(len(table.columns) for table in processed.tables),
                sum(len(table.foreign_keys) for table in schema.tables),
                sum(len(table.foreign_keys) for table in processed.tables),
                sum(column.description is not None for table in processed.tables for column in table.columns),
            ]
        )
    print()
    print("### Preprocessed Schema Statistics")
    print()
    print(
        tabulate(
            rows,
            headers=(
                "database",
                "columns",
                "processed_columns",
                "foreign_keys",
                "processed_foreign_keys",
                "descriptions",
            ),
            tablefmt=table_format,
        )
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Print schema and ambiguity statistics for a benchmark split.")
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", nargs="+")
    parser.add_argument("--table-format", default="github")
    parser.add_argument("--preprocessed-schema", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    started_at = time.perf_counter()
    cache_mode: Literal["off", "read_write"] = "off" if args.no_cache else "read_write"
    config = (
        Neo4jConnectorConfig(schema_cache_mode=cache_mode)
        if args.dataset == "cypherbench"
        else SQLConnectorConfig(schema_cache_mode=cache_mode)
    )
    loader_class: Any = dataset_registry.get_class(args.dataset)
    loader = loader_class(connector_config=config)
    dataset = await loader.get_split_async(args.split, databases=args.databases)
    if not dataset.db_connectors:
        raise ValueError("Dataset contains no databases")
    print(f"Loaded dataset in {time.perf_counter() - started_at:.2f} seconds\n")

    print_basic_stats(dataset, args.table_format)
    if args.preprocessed_schema:
        await print_preprocessed_schema_stats(dataset, args.table_format)

    ambiguity_tasks = [task for task in dataset.tasks if isinstance(task, AmbigNL2QTask)]
    if ambiguity_tasks:
        if len(ambiguity_tasks) != len(dataset.tasks):
            raise ValueError("Dataset mixes ambiguous and non-ambiguous tasks")
        print_ambiguity_stats(ambiguity_tasks, sorted(dataset.db_connectors), args.table_format)


if __name__ == "__main__":
    asyncio.run(main())
