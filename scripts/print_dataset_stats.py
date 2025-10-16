import argparse
import math
import time
import asyncio
import os
from tabulate import tabulate
from mintq.datahub import dataset_registry
from mintq.metadata_synthesizers import SchemaCompressor
from mintq.schema import NL2QDataset


def print_ambig_stats(dataset: NL2QDataset) -> None:
    db_names = list(dataset.db_connectors.keys())

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
        db = task.db
        unique_ambs = list(set([ap.ambiguity_type for ap in task.gold_ambiguity_points]))
        for amb in unique_ambs:
            db2counts[db][amb] += 1
    headers = ["Ambiguity"] + db_names + ["Total"]
    df = []
    for amb in ambiguities:
        counts = [db2counts[db][amb] for db in db_names]
        df.append((amb, *counts, sum(counts)))
    df.append(
        ("Total", *[len([task for task in dataset.tasks if task.db == db]) for db in db_names], len(dataset.tasks))
    )
    print()
    print("### Ambiguity Type Stats")
    print("note: this is the number of tasks with at least one corresponding ambiguity type")
    print()
    print(tabulate(df, headers=headers, tablefmt="github"))

    # Print number of ambiguity points per task
    headers = ["Number of AP"] + db_names + ["Total"]
    max_ap = max([len(task.gold_ambiguity_points) for task in dataset.tasks])
    df = []
    for i in range(1, max_ap + 1):
        row = (
            [f"{i} AP"]
            + [
                sum([1 for task in dataset.tasks if len(task.gold_ambiguity_points) == i and task.db == db])
                for db in db_names
            ]
            + [sum([1 for task in dataset.tasks if len(task.gold_ambiguity_points) == i])]
        )
        df.append(row)
    df.append(
        ("Total", *[len([task for task in dataset.tasks if task.db == db]) for db in db_names], len(dataset.tasks))
    )
    print()
    print("### Number of Ambiguity Points (AP) Stats")
    print()
    print(tabulate(df, headers=headers, tablefmt="github"))

    # Print distrubtion of parameter_dtype in infinite ambiguity points
    print("note: this is the number of ambiguity points with the corresponding parameter_dtype")
    db2counts = {db: {dtype: 0 for dtype in ["int", "float", "str"]} for db in db_names}
    for task in dataset.tasks:
        for ap in task.gold_ambiguity_points:
            if ap.type == "infinite":
                db2counts[task.db][ap.parameter_dtype] += 1
    headers = ["parameter_dtype"] + db_names + ["Total"]
    df = []
    for dtype in ["int", "float", "str"]:
        df.append((dtype, *[db2counts[db][dtype] for db in db_names], sum(db2counts[db][dtype] for db in db_names)))
    total_counts_per_db = [sum(db2counts[db][dtype] for dtype in ["int", "float", "str"]) for db in db_names]
    df.append(("Total", *total_counts_per_db, sum(total_counts_per_db)))
    print()
    print("### Distribution of parameter_dtype in Infinite Ambiguity Points")
    print()
    print(tabulate(df, headers=headers, tablefmt="github"))

    # Print distrubtion of total number of interpretation combinations
    num_intp = []
    for task in dataset.tasks:
        num_intp.append(math.prod(len(ap.interpretations) for ap in task.gold_ambiguity_points if ap.type == "finite"))
    headers = ["Number of Interpretation Combinations", "Tasks"]
    df = []
    unqiue_num = sorted(set(num_intp))
    for n in unqiue_num:
        df.append((n, num_intp.count(n)))
    df.append(("Total", sum(num_intp.count(n) for n in unqiue_num)))
    print()
    print("### Distribution of Total Number of Interpretation Combinations")
    print()
    print(tabulate(df, headers=headers, tablefmt="github"))

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="spider2-snow")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--format", default="github")
    parser.add_argument("--no_cache", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    if args.no_cache:
        os.environ["MINTQ_CACHE_ENABLED"] = "0"

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    per_db_stats = {
        "database": [],
        "tables": [],
        "tables_compressed": [],
        "columns": [],
        "columns_compressed": [],
        "ratio_columns_with_desc": [],
    }  # type: ignore
    db_names = sorted(dataset.db_connectors.keys())
    for db_name in db_names:
        schema = dataset.db_connectors[db_name].schema
        compressed_schema = await SchemaCompressor().run_async(schema)
        per_db_stats["database"].append(db_name)
        per_db_stats["tables"].append(len(schema.tables))
        per_db_stats["tables_compressed"].append(len(compressed_schema.tables))
        per_db_stats["columns"].append(sum(len(table.columns) for table in schema.tables))
        per_db_stats["columns_compressed"].append(sum(len(table.columns) for table in compressed_schema.tables))
        per_db_stats["ratio_columns_with_desc"].append(
            sum(1 for table in schema.tables for column in table.columns if column.description is not None)
            / per_db_stats["columns"][-1]
        )
    print()
    print("### Per-Database Stats")
    print()
    print(tabulate(per_db_stats, headers=list(per_db_stats.keys()), tablefmt=args.format, floatfmt=".2f"))

    aggregated_stats = {
        "dataset": args.dataset,
        "split": args.split,
        "total_tasks": len(dataset.tasks),
        "total_databases": len(dataset.db_connectors),
        "max_tables_per_db": max(per_db_stats["tables"]),
        "avg_tables_per_db": sum(per_db_stats["tables"]) / len(dataset.db_connectors),
        "min_tables_per_db": min(per_db_stats["tables"]),
        "max_tables_compressed_per_db": max(per_db_stats["tables_compressed"]),
        "avg_tables_compressed_per_db": sum(per_db_stats["tables_compressed"]) / len(dataset.db_connectors),
        "min_tables_compressed_per_db": min(per_db_stats["tables_compressed"]),
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
            tablefmt=args.format,
        )
    )
    if dataset.tasks[0].task_type == "ambig":
        print_ambig_stats(dataset)


if __name__ == "__main__":
    asyncio.run(main())
