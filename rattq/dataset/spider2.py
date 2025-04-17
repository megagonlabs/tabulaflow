import os
import json
import re
import random
import multiprocessing
from typing import Optional
import pandas as pd
from rattq.dataset.base import NL2QDatasetLoader
from rattq.schema import NL2QTask, NL2QDataset
from rattq.db_connector import SnowflakeConnector


def create_connector(args):
    name, conn_cls, kwargs = args
    return conn_cls(name, **kwargs)


class Spider2SnowDatasetLoader(NL2QDatasetLoader):
    def __init__(
        self,
        name: str = "spider2-snow",
        directory: str = "data/Spider2/spider2-snow",
        num_processes: int = 16,
        sf_user: Optional[str] = None,
        sf_password: Optional[str] = None,
        sf_account: Optional[str] = "YDB67606",
    ):
        self.name = name
        self.directory = directory
        self.num_processes = num_processes
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self._data = {}

    def _load_split(self, split: str) -> NL2QDataset:
        if split != "test":
            raise ValueError(f"Only test split is supported for spider2-snow")

        all_gold_exec_result_files = os.listdir(os.path.join(self.directory, "evaluation_suite", "gold", "exec_result"))

        tasks = []
        with open(os.path.join(self.directory, f"spider2-snow.jsonl"), "r") as f:
            for line in f:
                item = json.loads(line)

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

                pattern = re.compile(rf'^{re.escape(item["instance_id"])}(_[a-z])?\.csv$')
                gold_exec_result_files = [file for file in all_gold_exec_result_files if re.match(pattern, file)]
                gold_exec_result = []
                for file in gold_exec_result_files:
                    with open(os.path.join(self.directory, "evaluation_suite", "gold", "exec_result", file), "r") as f:
                        gold_exec_result.append(pd.read_csv(f))

                tasks.append(
                    NL2QTask(
                        qid=item["instance_id"],
                        language="SnowflakeSQL",
                        db=item["db_id"],
                        question=item["instruction"],
                        evidence=evidence,
                        gold_query=gold_sql,
                        gold_exec_result=gold_exec_result,
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

        with multiprocessing.Pool(processes=self.num_processes) as pool:
            db_connectors = pool.map(
                create_connector,
                [
                    (
                        name,
                        SnowflakeConnector,
                        {
                            "sf_user": sf_user,
                            "sf_password": sf_password,
                            "sf_account": sf_account,
                            "sf_database": name,
                            "sf_schema": name,
                        },
                    )
                    for name in db_names
                ],
            )
            db_connectors = {conn.name: conn for conn in db_connectors}

        return NL2QDataset(
            name=self.name,
            split_id=split,
            tasks=tasks,
            db_connectors=db_connectors,
        )

    def get_split(self, split_id: str) -> NL2QDataset:
        if "_" in split_id:
            split, sample_size = split_id.split("_")
        else:
            split, sample_size = split_id, None

        if split not in self._data:
            self._data[split] = self._load_split(split)

        if sample_size:
            sampler = random.Random(42)
            return NL2QDataset(
                name=self.name,
                split_id=split_id,
                tasks=sampler.sample(self._data[split].tasks, int(sample_size)),
                db_connectors=self._data[split].db_connectors,
            )
        else:
            return self._data[split]
