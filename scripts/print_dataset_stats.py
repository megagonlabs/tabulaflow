import argparse
import time
import asyncio
import os
from tabulate import tabulate
from mintq.datahub import dataset_registry


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

    per_db_stats = {"database": [], "num_tables": [], "num_columns": [], "ratio_columns_with_description": []}  # type: ignore
    db_names = sorted(dataset.db_connectors.keys())
    for db_name in db_names:
        schema = dataset.db_connectors[db_name].schema
        per_db_stats["database"].append(db_name)
        per_db_stats["num_tables"].append(len(schema.tables))
        per_db_stats["num_columns"].append(sum(len(table.columns) for table in schema.tables))
        per_db_stats["ratio_columns_with_description"].append(
            sum(1 for table in schema.tables for column in table.columns if column.description is not None)
            / per_db_stats["num_columns"][-1]
        )
    print()
    print("### Per-Database Stats")
    print(tabulate(per_db_stats, headers=list(per_db_stats.keys()), tablefmt=args.format, floatfmt=".2f"))

    aggregated_stats = {
        "dataset": args.dataset,
        "split": args.split,
        "total_tasks": len(dataset.tasks),
        "total_databases": len(dataset.db_connectors),
        "max_tables_per_db": max(per_db_stats["num_tables"]),
        "avg_tables_per_db": sum(per_db_stats["num_tables"]) / len(dataset.db_connectors),
        "min_tables_per_db": min(per_db_stats["num_tables"]),
        "max_columns_per_db": max(per_db_stats["num_columns"]),
        "avg_columns_per_db": sum(per_db_stats["num_columns"]) / len(dataset.db_connectors),
        "min_columns_per_db": min(per_db_stats["num_columns"]),
        "avg_columns_per_table": sum(per_db_stats["num_columns"]) / sum(per_db_stats["num_tables"]),
        "avg_ratio_columns_with_description": sum(per_db_stats["ratio_columns_with_description"])
        / len(dataset.db_connectors),
    }
    print()
    print("### Aggregated Stats")
    print(
        tabulate(
            [(k, round(v, 2) if isinstance(v, float) else v) for k, v in aggregated_stats.items()],
            headers=("key", "value"),
            tablefmt=args.format,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
