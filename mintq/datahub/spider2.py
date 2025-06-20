import os
import json
import re
import random
import asyncio
from urllib.parse import quote_plus
from typing import Optional, Any, Literal
import pandas as pd
from mintq.schema import SimpleNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector


class Spider2SnowDatasetLoader:
    name = "spider2-snow"

    def __init__(
        self,
        directory: str = "data/Spider2/spider2-snow",
        sf_user: Optional[str] = None,
        sf_password: Optional[str] = None,
        sf_account: Optional[str] = None,
    ):
        self.directory = directory
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self._data: dict[Any, NL2QDataset] = {}

        # The default warehouse for Spider2 snowflake is "small" which allows for 16 concurrent queries
        self._dbms_semaphore = asyncio.Semaphore(16)

    async def _load_split_async(self, split: Literal["dev"], databases: Optional[list[str]] = None) -> NL2QDataset:
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
                    SimpleNL2QTask(
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
            sf_user = os.environ["SF_USER"]
        if sf_password is None:
            sf_password = os.environ["SF_PASSWORD"]
        if sf_account is None:
            sf_account = os.environ["SF_ACCOUNT"]

        encoded_user = quote_plus(sf_user)
        encoded_password = quote_plus(sf_password)
        base_url = f"snowflake://{encoded_user}:{encoded_password}@{sf_account}"

        connect_args = {
            "disable_ocsp_checks": True,
            "client_session_keep_alive": True,
        }

        # We use a higher per-db concurrency for loading schemas
        schemas = []
        for name in db_names:
            db_conn = await SQLConnector.from_url_async(
                name, "sync", f"{base_url}/{name}", max_concurrency_per_db=2, connect_args=connect_args
            )
            schemas.append(db_conn.schema)

        # We set the per-db concurrency to 2 because there are 151 databases so we can have up to 151 x 2 = 302 concurrent connections
        db_connectors = [
            await SQLConnector.from_url_async(
                name,
                "sync",
                f"{base_url}/{name}",
                max_concurrency_per_db=2,
                dbms_semaphore=self._dbms_semaphore,
                schema=schema,
                connect_args=connect_args,
            )
            for name, schema in zip(db_names, schemas)
        ]

        return NL2QDataset(
            name=self.name,
            split_id=split,
            databases=databases,
            tasks=tasks,  # type: ignore
            db_connectors={conn.name: conn for conn in db_connectors},
        )

    async def get_split_async(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if "_" in split_id:
            split, sample_size = split_id.split("_")
        else:
            split, sample_size = split_id, None

        if sample_size and databases:
            raise ValueError("sample_size and databases cannot be both specified")

        key = tuple(sorted(databases)) if isinstance(databases, list) else None

        if (split, key) not in self._data:
            self._data[(split, key)] = await self._load_split_async(split, databases=databases)

        dataset = self._data[(split, key)]
        if sample_size:
            sampler = random.Random(42)
            return NL2QDataset(
                name=self.name,
                split_id=split_id,
                databases=databases,
                tasks=sampler.sample(dataset.tasks, int(sample_size)),
                db_connectors=dataset.db_connectors,
            )
        else:
            return dataset


class Spider2SimpleDatasetLoader:
    name = "spider2-simple"

    def __init__(
        self,
        directory: str = "data/Spider2/spider2-snow",
        task_csv_path: str = "data/spider2-simple/spider2-simple-v1.csv",
        sf_user: Optional[str] = None,
        sf_password: Optional[str] = None,
        sf_account: Optional[str] = None,
    ):
        self.directory = directory
        self.task_csv_path = task_csv_path
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self._data: dict[Any, NL2QDataset] = {}

        # The default warehouse for Spider2 snowflake is "small" which allows for 16 concurrent queries
        self._dbms_semaphore = asyncio.Semaphore(16)

    async def _load_split_async(self, split: Literal["dev"], databases: Optional[list[str]] = None) -> NL2QDataset:
        qid_to_evidence = {}
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

                qid_to_evidence[item["instance_id"]] = evidence

        df = pd.read_csv(self.task_csv_path)
        tasks = []
        for _, row in df.iterrows():
            qid = row["instance"]
            if qid.endswith(".sql"):
                qid = qid[:-4]

            tasks.append(
                SimpleNL2QTask(
                    qid=qid,
                    language="SnowflakeSQL",
                    db=row["db"],
                    question=row["instruction"],
                    evidence=qid_to_evidence[qid],
                    gold_queries=[row["sql"]],
                    gold_exec_results=[],
                    extra_info={},
                )
            )

        db_names = list(dict.fromkeys([task.db for task in tasks]))

        sf_user, sf_password, sf_account = self.sf_user, self.sf_password, self.sf_account
        if sf_user is None:
            sf_user = os.environ["SF_USER"]
        if sf_password is None:
            sf_password = os.environ["SF_PASSWORD"]
        if sf_account is None:
            sf_account = os.environ["SF_ACCOUNT"]

        encoded_user = quote_plus(sf_user)
        encoded_password = quote_plus(sf_password)
        base_url = f"snowflake://{encoded_user}:{encoded_password}@{sf_account}"

        connect_args = {
            "disable_ocsp_checks": True,
            "client_session_keep_alive": True,
        }

        # We use a higher per-db concurrency for loading schemas
        schemas = []
        for name in db_names:
            db_conn = await SQLConnector.from_url_async(
                name, "sync", f"{base_url}/{name}", max_concurrency_per_db=2, connect_args=connect_args
            )
            schemas.append(db_conn.schema)

        # We set the per-db concurrency to 2 because there are 151 databases so we can have up to 151 x 2 = 302 concurrent connections
        db_connectors = [
            await SQLConnector.from_url_async(
                name,
                "sync",
                f"{base_url}/{name}",
                max_concurrency_per_db=2,
                dbms_semaphore=self._dbms_semaphore,
                schema=schema,
                connect_args=connect_args,
            )
            for name, schema in zip(db_names, schemas)
        ]

        return NL2QDataset(
            name=self.name,
            split_id=split,
            databases=databases,
            tasks=tasks,  # type: ignore
            db_connectors={conn.name: conn for conn in db_connectors},
        )

    async def get_split_async(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if "_" in split_id:
            split, sample_size = split_id.split("_")
        else:
            split, sample_size = split_id, None

        if sample_size and databases:
            raise ValueError("sample_size and databases cannot be both specified")

        key = tuple(sorted(databases)) if isinstance(databases, list) else None

        if (split, key) not in self._data:
            self._data[(split, key)] = await self._load_split_async(split, databases=databases)

        dataset = self._data[(split, key)]
        if sample_size:
            sampler = random.Random(42)
            return NL2QDataset(
                name=self.name,
                split_id=split_id,
                databases=databases,
                tasks=sampler.sample(dataset.tasks, int(sample_size)),
                db_connectors=dataset.db_connectors,
            )
        else:
            return dataset
