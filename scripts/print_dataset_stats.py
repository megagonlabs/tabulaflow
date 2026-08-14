# mypy: ignore-errors
import argparse
import time
import asyncio
from tabulate import tabulate
import tabulaflow
from tabulaflow.research.benchmarks import dataset_registry
from tabulaflow.data.schema_compressor import SchemaCompressor
from tabulaflow.agents.modules.schema_preprocessor import SchemaPreprocessor
from tabulaflow.research.types import NL2QDataset
from tabulaflow.research.utils import dict_to_df


MAX_DBS_TO_PRINT = 12


async def print_per_db_ambig_stats(dataset: NL2QDataset, tablefmt: str = "github") -> None:
    assert all(task.task_type == "ambig" for task in dataset.tasks)
    db_names = list(dataset.db_connectors.keys())

    total_column_only = len(dataset.db_connectors) > MAX_DBS_TO_PRINT

    # Print stats for ambiguity types
    ambiguities = [
        "semantic_column",
        "semantic_table",
        "semantic_value",
        "semantic_computation",
        "syntactic_column",
        "syntactic_table",
        "syntactic_value",
        "syntactic_computation",
    ]
    db2counts = {db: {amb: 0 for amb in ambiguities} for db in db_names}
    for task in dataset.tasks:
        unique_ambs = list(set([ap.ambiguity_type for ap in task.gold_ambiguity_points]))
        for amb in unique_ambs:
            db2counts[task.db][amb] += 1
    print()
    print("### Ambiguity Type Stats")
    print("note: this is the number of tasks with at least one corresponding ambiguity type")
    print()
    print(tabulate(dict_to_df(db2counts, total_column_only=total_column_only), headers="keys", tablefmt=tablefmt))

    # Print number of ambiguity points per task
    max_ap = max([len(task.gold_ambiguity_points) for task in dataset.tasks])
    db2counts = {db: {ap: 0 for ap in range(1, max_ap + 1)} for db in db_names}
    for task in dataset.tasks:
        db2counts[task.db][len(task.gold_ambiguity_points)] += 1
    print()
    print("### Number of Ambiguity Points (AP) Stats")
    print()
    print(tabulate(dict_to_df(db2counts, total_column_only=total_column_only), headers="keys", tablefmt=tablefmt))

    # Print distrubtion of parameter_dtype in infinite ambiguity points
    db2counts = {db: {dtype: 0 for dtype in ["int", "float", "str"]} for db in db_names}
    for task in dataset.tasks:
        for ap in task.gold_ambiguity_points:
            if ap.type == "infinite":
                db2counts[task.db][ap.parameter_dtype] += 1
    print()
    print("### Distribution of parameter_dtype in Infinite Ambiguity Points")
    print("note: this is the number of ambiguity points with the corresponding parameter_dtype")
    print()
    print(tabulate(dict_to_df(db2counts, total_column_only=total_column_only), headers="keys", tablefmt=tablefmt))

    # Print distrubtion of total number of interpretation combinations
    num_intp = sorted(set([len(task.gold_queries) for task in dataset.tasks]))
    db2counts = {db: {n: 0 for n in num_intp} for db in db_names}
    for task in dataset.tasks:
        db2counts[task.db][len(task.gold_queries)] += 1
    print()
    print("### Distribution of Total Number of Interpretation Combinations")
    print("note: this is the number of tasks with the corresponding number of interpretation combinations")
    print()
    print(tabulate(dict_to_df(db2counts, total_column_only=total_column_only), headers="keys", tablefmt=tablefmt))


async def print_aggregated_ambig_stats(dataset: NL2QDataset, tablefmt: str = "github") -> None:
    finite_ambig_points = [sum(1 for ap in task.gold_ambiguity_points if ap.type == "finite") for task in dataset.tasks]
    infinite_ambig_points = [
        sum(1 for ap in task.gold_ambiguity_points if ap.type == "infinite") for task in dataset.tasks
    ]
    aggregated_stats = {
        "max_ambig_points": max([len(task.gold_ambiguity_points) for task in dataset.tasks]),
        "avg_ambig_points": sum([len(task.gold_ambiguity_points) for task in dataset.tasks]) / len(dataset.tasks),
        "min_ambig_points": min([len(task.gold_ambiguity_points) for task in dataset.tasks]),
        "max_finite_ambig_points": max(finite_ambig_points),
        "avg_finite_ambig_points": sum(finite_ambig_points) / len(dataset.tasks),
        "min_finite_ambig_points": min(finite_ambig_points),
        "max_infinite_ambig_points": max(infinite_ambig_points),
        "avg_infinite_ambig_points": sum(infinite_ambig_points) / len(dataset.tasks),
        "min_infinite_ambig_points": min(infinite_ambig_points),
        "max_intp_combinations": max([len(task.gold_queries) for task in dataset.tasks]),
        "avg_intp_combinations": sum([len(task.gold_queries) for task in dataset.tasks]) / len(dataset.tasks),
        "min_intp_combinations": min([len(task.gold_queries) for task in dataset.tasks]),
    }
    print()
    print("### Aggregated Ambiguity Stats")
    print()
    print(
        tabulate(
            [(k, round(v, 2) if isinstance(v, float) else v) for k, v in aggregated_stats.items()],
            headers=("key", "value"),
            tablefmt=tablefmt,
        )
    )


async def print_basic_stats(dataset: NL2QDataset, tablefmt: str = "github") -> None:
    per_db_stats = {
        "database": [],
        "tables": [],
        "tables_compressed": [],
        "total_rows": [],
        "max_rows_per_table": [],
        "columns": [],
        "columns_compressed": [],
        "ratio_columns_with_desc": [],
    }  # type: ignore
    db_names = sorted(dataset.db_connectors.keys())
    for db_name in db_names:
        schema = dataset.db_connectors[db_name].schema
        compressed_schema = SchemaCompressor().compress(schema)
        per_db_stats["database"].append(db_name)
        per_db_stats["tables"].append(len(schema.tables))
        per_db_stats["tables_compressed"].append(len(compressed_schema.tables))
        per_db_stats["total_rows"].append(sum(table.num_rows for table in schema.tables if table.num_rows is not None))
        per_db_stats["max_rows_per_table"].append(
            max((table.num_rows for table in schema.tables if table.num_rows is not None), default=0)
        )
        per_db_stats["columns"].append(sum(len(table.columns) for table in schema.tables))
        per_db_stats["columns_compressed"].append(sum(len(table.columns) for table in compressed_schema.tables))
        per_db_stats["ratio_columns_with_desc"].append(
            sum(1 for table in schema.tables for column in table.columns if column.description is not None)
            / per_db_stats["columns"][-1]
        )
    if len(dataset.db_connectors) < MAX_DBS_TO_PRINT:
        print()
        print("### Per-Database Stats")
        print()
        print(tabulate(per_db_stats, headers=list(per_db_stats.keys()), tablefmt=tablefmt, floatfmt=".2f"))

    aggregated_stats = {
        "dataset": dataset.name,
        "split": dataset.split,
        "total_tasks": len(dataset.tasks),
        "total_databases": len(dataset.db_connectors),
        "max_tables_per_db": max(per_db_stats["tables"]),
        "avg_tables_per_db": sum(per_db_stats["tables"]) / len(dataset.db_connectors),
        "min_tables_per_db": min(per_db_stats["tables"]),
        "max_tables_compressed_per_db": max(per_db_stats["tables_compressed"]),
        "avg_tables_compressed_per_db": sum(per_db_stats["tables_compressed"]) / len(dataset.db_connectors),
        "min_tables_compressed_per_db": min(per_db_stats["tables_compressed"]),
        "max_rows_per_db": max(per_db_stats["total_rows"]),
        "avg_rows_per_db": sum(per_db_stats["total_rows"]) / len(dataset.db_connectors),
        "min_rows_per_db": min(per_db_stats["total_rows"]),
        "max_max_rows_per_table": max(per_db_stats["max_rows_per_table"]),
        "avg_max_rows_per_table": sum(per_db_stats["max_rows_per_table"]) / len(dataset.db_connectors),
        "min_max_rows_per_table": min(per_db_stats["max_rows_per_table"]),
        "max_columns_per_db": max(per_db_stats["columns"]),
        "avg_columns_per_db": sum(per_db_stats["columns"]) / len(dataset.db_connectors),
        "min_columns_per_db": min(per_db_stats["columns"]),
        "max_columns_compressed_per_db": max(per_db_stats["columns_compressed"]),
        "avg_columns_compressed_per_db": sum(per_db_stats["columns_compressed"]) / len(dataset.db_connectors),
        "min_columns_compressed_per_db": min(per_db_stats["columns_compressed"]),
        "avg_columns_per_table": sum(per_db_stats["columns"]) / sum(per_db_stats["tables"]),
        "avg_ratio_columns_with_desc": sum(per_db_stats["ratio_columns_with_desc"]) / len(dataset.db_connectors),
    }
    print()
    print("### Aggregated Stats")
    print()
    print(
        tabulate(
            [(k, round(v, 2) if isinstance(v, float) else v) for k, v in aggregated_stats.items()],
            headers=("key", "value"),
            tablefmt=tablefmt,
        )
    )


async def print_preprocessed_schema_stats(dataset: NL2QDataset, tablefmt: str = "github") -> None:
    per_db_stats = {
        "database": [],
        "columns": [],
        "columns_preprocessed": [],
        "FKs": [],
        "FKs_preprocessed": [],
        "concise_desc": [],
        "detailed_desc": [],
    }  # type: ignore

    preprocessor = SchemaPreprocessor()

    db_names = sorted(dataset.db_connectors.keys())
    for db_name in db_names:
        schema = dataset.db_connectors[db_name].schema
        preprocessed_schema = await preprocessor.preprocess_async(dataset.db_connectors[db_name])
        per_db_stats["database"].append(db_name)
        per_db_stats["columns"].append(sum(len(table.columns) for table in schema.tables))
        per_db_stats["columns_preprocessed"].append(sum(len(table.columns) for table in preprocessed_schema.tables))
        per_db_stats["FKs"].append(sum(len(table.foreign_keys) for table in schema.tables))
        per_db_stats["FKs_preprocessed"].append(sum(len(table.foreign_keys) for table in preprocessed_schema.tables))
        per_db_stats["concise_desc"].append(
            sum(1 for table in preprocessed_schema.tables for column in table.columns if column.description is not None)
        )
        per_db_stats["detailed_desc"].append(
            sum(
                1
                for table in preprocessed_schema.tables
                for column in table.columns
                if column.detailed_description_markdown is not None
            )
        )
    if len(dataset.db_connectors) < MAX_DBS_TO_PRINT:
        print()
        print("### Preprocessed Schema Stats")
        print()
        print(tabulate(per_db_stats, headers=list(per_db_stats.keys()), tablefmt=tablefmt, floatfmt=".2f"))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", default=None, nargs="+")
    parser.add_argument("--format", default="github")
    parser.add_argument("--print_preprocessed_schema_stats", action="store_true")
    parser.add_argument("--no_cache", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    tabulaflow.configure(schema_cache_enabled=not args.no_cache)

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    await print_basic_stats(dataset, args.format)
    if args.print_preprocessed_schema_stats:
        await print_preprocessed_schema_stats(dataset, args.format)

    if dataset.tasks[0].task_type == "ambig":
        await print_per_db_ambig_stats(dataset, args.format)
        await print_aggregated_ambig_stats(dataset, args.format)


if __name__ == "__main__":
    asyncio.run(main())
