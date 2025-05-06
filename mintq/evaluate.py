import argparse
import copy
import json
import os
import time
from tqdm import tqdm
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from mintq.db_connector import BaseDBConnector
from mintq.schema import NL2QTask
from mintq.utils import avg_and_round, load_nl2q_tasks
from mintq.dataset import get_dataset_loader
from mintq.metric import get_metric


def compute_metrics(item: NL2QTask, metrics: list[str], db_connector: BaseDBConnector):
    item = copy.deepcopy(item)
    for m in metrics:
        pred_query = item.pred_query
        if pred_query.endswith("<end_of_turn>"):
            pred_query = pred_query[: -len("<end_of_turn>")].strip()
        item.metrics[m] = get_metric(m).compute(task=item, db_connector=db_connector)
    return item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="spider2-snow")
    parser.add_argument("--split", default="test")
    parser.add_argument("--evaluate_on_intersection", action="store_true")
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--num_threads", type=int, default=8)
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=[
            "bird_sql_ex",
            "bird_sql_ex_soft",
            "executable",
            "gold_executable",
            "gold_result_not_empty",
        ],
    )
    args = parser.parse_args()
    if args.dataset == "bird-sql":
        parser.set_defaults(split="dev")
    elif args.dataset == "spider2-snow":
        parser.set_defaults(split="test")
    args = parser.parse_args()
    print(args)
    print()

    result = load_nl2q_tasks(os.path.join(args.result_dir, "result.json"))
    databases = list(dict.fromkeys([item.db for item in result]))

    t0 = time.time()
    dataset_loader = get_dataset_loader(args.dataset)
    dataset = dataset_loader.get_split(args.split, databases=databases)
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    if args.evaluate_on_intersection:
        qid2item = {item.qid: item for item in result}
        result = [qid2item[item.qid] for item in dataset.tasks if item.qid in qid2item]

    # Shuffle the result to reduce concurent query execution on the same database
    qids = {item.qid: i for i, item in enumerate(result)}
    random.seed(42)
    random.shuffle(result)

    # Use ThreadPoolExecutor for multithreading
    result_with_metrics = []
    with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
        futures = [
            executor.submit(compute_metrics, item, args.metrics, dataset.db_connectors[item.db]) for item in result
        ]
        for future in tqdm(as_completed(futures), total=len(result)):
            result_with_metrics.append(future.result())

    # Sort the result by qid
    result_with_metrics.sort(key=lambda x: qids[x.qid])

    output_path = os.path.join(args.result_dir, "result_with_metrics.json")
    with open(output_path, "w") as fout:
        json.dump(
            [item.model_dump(mode="json") for item in result_with_metrics],
            fout,
            indent=2,
        )
    print(f"Saved result with metrics to {output_path}")

    output_path = os.path.join(args.result_dir, "aggregated_metrics.json")
    with open(output_path, "r") as fout:
        aggregated = json.load(fout)

    aggregated.update({m: avg_and_round([item.metrics[m] for item in result_with_metrics]) for m in args.metrics})

    with open(output_path, "w") as fout:
        json.dump(aggregated, fout, indent=2)
    print(f"Saved aggregated metrics to {output_path}")

    print()
    print("Aggregated metrics:")
    print(json.dumps(aggregated, indent=2))


if __name__ == "__main__":
    main()
