import argparse
import copy
import time
from tqdm import tqdm
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from mintq.db_connector import BaseDBConnector
from mintq.schema import NL2QTask, NL2QRunResult, NL2QDataset
from mintq.utils import avg_and_round
from mintq.dataset import get_dataset_loader
from mintq.metric import get_metric, NL2QMetric


def compute_metrics(item: NL2QTask, metrics: list[NL2QMetric], db_connector: BaseDBConnector):
    item = copy.deepcopy(item)
    for m in metrics:
        item.metrics[m.name] = m.compute(task=item, db_connector=db_connector)
    return item


def evaluate(result: NL2QRunResult, dataset: NL2QDataset, metrics: list[NL2QMetric], num_threads: int) -> NL2QRunResult:
    result = copy.deepcopy(result)

    # Shuffle the result to reduce concurent query execution on the same database
    qids = {item.qid: i for i, item in enumerate(result.tasks)}
    random.seed(42)
    random.shuffle(result.tasks)

    # Use ThreadPoolExecutor for multithreading
    tasks_with_metrics = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(compute_metrics, item, metrics, dataset.db_connectors[item.db]) for item in result.tasks
        ]
        for future in tqdm(as_completed(futures), total=len(result.tasks)):
            tasks_with_metrics.append(future.result())

    # Sort the result so that the order is the same as the original result
    tasks_with_metrics.sort(key=lambda x: qids[x.qid])
    result.tasks = tasks_with_metrics

    aggregated_metrics = {m.name: avg_and_round([item.metrics[m.name] for item in tasks_with_metrics]) for m in metrics}
    result.aggregated_metrics.update(aggregated_metrics)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_json", default="output/test/result.json")
    parser.add_argument("--num_threads", type=int, default=8)
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=[
            "spider2_ex",
            "bird_sql_ex",
            "bird_sql_ex_soft",
            "executable",
            "gold_executable",
            "gold_result_not_empty",
        ],
    )
    args = parser.parse_args()
    print(args)
    print()

    with open(args.result_json, "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    t0 = time.time()
    dataset_loader = get_dataset_loader(result.dataset)
    dataset = dataset_loader.get_split(result.split_id, databases=result.databases)
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {result.dataset} {result.split_id} set in {time.time() - t0:.2f} seconds."
    )

    metrics = [get_metric(m) for m in args.metrics]
    result = evaluate(result, dataset, metrics, args.num_threads)

    print()
    print("Aggregated metrics:")
    for m in metrics:
        print(f"- {m.name}: {result.aggregated_metrics[m.name]:.4f}")

    output_path = args.result_json.replace(".json", "_with_metrics.json")
    with open(output_path, "w") as fout:
        fout.write(result.model_dump_json(indent=2))
    print()
    print(f"Saved result with metrics to {output_path}")


if __name__ == "__main__":
    main()
