import argparse
import time
from mintq.dataset import get_dataset_loader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="spider2-snow")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", default=None, nargs="+")
    args = parser.parse_args()
    print(args)
    print()

    t0 = time.time()
    dataset_loader = get_dataset_loader(args.dataset)
    dataset = dataset_loader.get_split(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )


if __name__ == "__main__":
    main()
