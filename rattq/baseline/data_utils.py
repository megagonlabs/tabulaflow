import json
import os
from rattq.db_connector import BaseDBConnector, SQLiteConnector


def get_db_connectors(dataset_name: str) -> dict[str, BaseDBConnector]:
    if dataset_name == 'bird-sql':
        res = {}
        for metadata_path, db_dir in (
            ('data/BIRD-SQL/dev_20240627/dev_tables.json', 'data/BIRD-SQL/dev_20240627/dev_databases/'),
            ('data/BIRD-SQL/train/train_tables.json', 'data/BIRD-SQL/train/train_databases/')
        ):
            with open(metadata_path, 'r') as f:
                db_names = [item['db_id'] for item in json.load(f)]
            for db_name in db_names:
                sqlite_path = os.path.join(db_dir, db_name, f'{db_name}.sqlite')
                res[db_name] = SQLiteConnector(name=db_name, db_path=sqlite_path)
        return res
    else:
        raise ValueError(f'Dataset {dataset_name} not supported')