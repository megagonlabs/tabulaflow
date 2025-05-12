import argparse
import time
import os
from mintq.dataset import get_dataset_loader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="spider2-snow")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    t0 = time.time()
    dataset_loader = get_dataset_loader(args.dataset)
    dataset = dataset_loader.get_split(args.split)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    num_dbs = len(dataset.db_connectors)
    num_tables = sum(len(db.schema.tables) for db in dataset.db_connectors.values())
    num_columns = sum(sum(len(table.columns) for table in db.schema.tables) for db in dataset.db_connectors.values())

    db_to_columns = { name: sum(len(table.columns) for table in db.schema.tables) for name, db in dataset.db_connectors.items() }
    db_to_columns = dict(sorted(db_to_columns.items(), key=lambda x: x[0]))
    print()
    print("### Column counts per database")
    for db, columns in db_to_columns.items():
        print(f"- {db}: {columns}")

    print()
    print("### Overall stats")
    print(f"Dataset: {args.dataset}")
    print(f"Split: {args.split}")
    print(f"total_tasks: {len(dataset.tasks)}")
    print(f"total_databases: {num_dbs}")
    print(f"avg_tables_per_db: {num_tables / num_dbs:.2f}")
    print(f"avg_columns_per_table: {num_columns / num_tables:.2f}")
    print(f"avg_columns_per_db: {num_columns / num_dbs:.2f}")


if __name__ == "__main__":
    main()
