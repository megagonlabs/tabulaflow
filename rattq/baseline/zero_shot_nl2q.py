import argparse
import os
import shutil
from rattq.baseline.data_utils import get_db_connectors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--llm', default='gpt-4o')
    parser.add_argument('--prompt', default='default', choices=['default'])
    parser.add_argument('--dataset', default='bird-sql')
    parser.add_argument('--batch_size', default=10, type=int)
    parser.add_argument('--wait_time_between_batches', default=0.0, type=float)
    parser.add_argument('--result_dir', default='output/zero_shot_nl2q_gpt-4o/')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    print(args)
    print()

    if os.path.exists(args.result_dir):
        if not args.overwrite:
            print(f'{args.result_dir} already exists. Use --overwrite to overwrite the directory.')
            return
        else:
            shutil.rmtree(args.result_dir)
    os.makedirs(args.result_dir)

    db_connectors = get_db_connectors(args.dataset, splits=['dev'])
    for db_name, db_connector in db_connectors.items():
        print(db_name)
        print(db_connector.get_schema())

if __name__ == '__main__':
    main()
