import argparse
import copy
import json
import os
import math
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from rattq.metric import bird_sql_ex
from rattq.db_connector import BaseDBConnector
from rattq.schema import NL2QSample
from rattq.baseline.data_utils import get_db_connectors


METRIC_FUNC_MAPPING = {
    'bird_sql_ex': bird_sql_ex,
}


def compute_metrics(item: NL2QSample, metrics: list[str], db_connector: BaseDBConnector):
    item = copy.deepcopy(item)
    for m in metrics:
        pred_query = item.pred_query
        if pred_query.endswith('<end_of_turn>'):
            pred_query = pred_query[:-len('<end_of_turn>')].strip()
        item.metrics[m] = METRIC_FUNC_MAPPING[m](
            pred_query=pred_query,
            gold_query=item.gold_query,
            db_connector=db_connector
        )
    return item


def avg_and_round(nums: list[float], n: int = 4):
    return round(sum(nums) / len(nums), n) if nums else math.nan


def aggregate(results: list[tuple[str, float]]):
    res = {}
    for key, value in results:
        if key not in res:
            res[key] = []
        res[key].append(value)
    for key, values in res.items():
        res[key] = avg_and_round(values)
    return res


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='bird-sql')
    parser.add_argument('--split', default='dev')
    parser.add_argument('--result_dir', default='output/gpt-4o')
    parser.add_argument('--num_threads', type=int, default=8)
    parser.add_argument('--metrics', nargs='+', default=['bird_sql_ex'])
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir, 'result.json')) as fin:
        result = [NL2QSample(**item) for item in json.load(fin)]
    
    db_connectors = get_db_connectors(dataset_name=args.dataset, splits=[args.split])

    # Use ThreadPoolExecutor for multithreading
    result_with_metrics = []
    with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
        futures = [executor.submit(compute_metrics, item, args.metrics, db_connectors[item.db]) for item in result]
        for future in tqdm(as_completed(futures), total=len(result)):
            result_with_metrics.append(future.result())

    aggregated = {}
    aggregated['overall'] = {m: avg_and_round([item.metrics[m] for item in result_with_metrics]) for m in args.metrics}

    output_path = os.path.join(args.result_dir, f'result_with_metrics.json')
    with open(output_path, 'w') as fout:
        json.dump([item.model_dump(mode='json') for item in result_with_metrics], fout, indent=2)
    print(f'Saved result with metrics to {output_path}')

    output_path = os.path.join(args.result_dir, f'aggregated_metrics.json')
    with open(output_path, 'w') as fout:
        json.dump(aggregated, fout, indent=2)
    print(f'Saved aggregated metrics to {output_path}')

    print()
    print('Aggregated metrics:')
    print(json.dumps(aggregated, indent=2))


if __name__ == '__main__':
    main()