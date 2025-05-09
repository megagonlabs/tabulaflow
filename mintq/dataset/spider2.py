import os
import json
import re
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import pandas as pd
from tqdm import tqdm
from mintq.dataset.base import NL2QDatasetLoader
from mintq.schema import SingleOutputNL2QTask, NL2QDataset
from mintq.db_connector import SnowflakeConnector


def create_connector(args):
    name, conn_cls, kwargs = args
    return conn_cls(name, **kwargs)


class Spider2SnowDatasetLoader(NL2QDatasetLoader):
    def __init__(
        self,
        name: str = "spider2-snow",
        directory: str = "data/Spider2/spider2-snow",
        num_threads: int = 16,
        sf_user: Optional[str] = None,
        sf_password: Optional[str] = None,
        sf_account: Optional[str] = None,
    ):
        self.name = name
        self.directory = directory
        self.num_threads = num_threads
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self._data = {}

    def _load_split(self, split: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if split != "test":
            raise ValueError("Only test split is supported for spider2-snow")

        all_gold_exec_result_files = os.listdir(os.path.join(self.directory, "evaluation_suite", "gold", "exec_result"))

        # Load spider2snow_eval.jsonl
        eval_standard_file = os.path.join(self.directory, "evaluation_suite", "gold", "spider2snow_eval.jsonl")
        eval_standard = {}
        with open(eval_standard_file, "r") as f:
            for line in f:
                item = json.loads(line)
                qid = item.pop("instance_id")
                eval_standard[qid] = item

        tasks = []
        with open(os.path.join(self.directory, "spider2-snow.jsonl"), "r") as f:
            for line in f:
                item = json.loads(line)

                if databases and item["db_id"] not in databases:
                    continue

                if item["external_knowledge"]:
                    evidence_file = os.path.join(self.directory, "resource", "documents", item["external_knowledge"])
                    with open(evidence_file, "r") as f:
                        evidence = f.read()
                else:
                    evidence = None

                gold_sql_file = os.path.join(
                    self.directory, "evaluation_suite", "gold", "sql", item["instance_id"] + ".sql"
                )
                if os.path.exists(gold_sql_file):
                    with open(gold_sql_file, "r") as f:
                        gold_sql = [f.read()]
                else:
                    gold_sql = []

                pattern = re.compile(rf"^{re.escape(item['instance_id'])}(_[a-z])?\.csv$")
                gold_exec_result_files = [file for file in all_gold_exec_result_files if re.match(pattern, file)]
                gold_exec_result_files = sorted(gold_exec_result_files)  # must load from a to z
                gold_exec_results = []
                for file in gold_exec_result_files:
                    with open(os.path.join(self.directory, "evaluation_suite", "gold", "exec_result", file), "r") as f:
                        gold_exec_results.append(pd.read_csv(f).to_dict(orient="records"))

                tasks.append(
                    SingleOutputNL2QTask(
                        qid=item["instance_id"],
                        language="SnowflakeSQL",
                        db=item["db_id"],
                        question=item["instruction"],
                        evidence=evidence,
                        gold_queries=gold_sql,
                        gold_exec_results=gold_exec_results,
                        extra_info=eval_standard[item["instance_id"]],
                    )
                )

        db_names = list(dict.fromkeys([task.db for task in tasks]))

        sf_user, sf_password, sf_account = self.sf_user, self.sf_password, self.sf_account
        if sf_user is None:
            sf_user = os.environ.get("SF_USER")
        if sf_password is None:
            sf_password = os.environ.get("SF_PASSWORD")
        if sf_account is None:
            sf_account = os.environ.get("SF_ACCOUNT")

        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            connector_args = [
                (
                    name,
                    SnowflakeConnector,
                    {"sf_user": sf_user, "sf_password": sf_password, "sf_account": sf_account, "sf_database": name},
                )
                for name in db_names
            ]
            db_connectors = list(
                tqdm(
                    executor.map(create_connector, connector_args),
                    total=len(connector_args),
                    desc="Creating database connectors",
                )
            )
            db_connectors = {conn.name: conn for conn in db_connectors}

        return NL2QDataset(
            name=self.name,
            split_id=split,
            tasks=tasks,
            db_connectors=db_connectors,
        )

    def get_split(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if "_" in split_id:
            split, sample_size = split_id.split("_")
        else:
            split, sample_size = split_id, None

        if sample_size and databases:
            raise ValueError("sample_size and databases cannot be both specified")

        if databases:
            databases = tuple(sorted(databases))

        if (split, databases) not in self._data:
            self._data[(split, databases)] = self._load_split(split, databases=databases)

        dataset = self._data[(split, databases)]
        if sample_size:
            sampler = random.Random(42)
            return NL2QDataset(
                name=self.name,
                split_id=split_id,
                tasks=sampler.sample(dataset.tasks, int(sample_size)),
                db_connectors=dataset.db_connectors,
            )
        else:
            return dataset
