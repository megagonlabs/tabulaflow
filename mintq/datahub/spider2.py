import os
import json
import re
import random
import asyncio
from urllib.parse import quote_plus
from typing import Optional, Any, Literal, ClassVar
import pandas as pd
from mintq.schema import SimpleNL2QTask, NL2QDataset, NL2QTask, GoldQuery, ExecResult
from mintq.db_connector import SQLConnector, BaseAsyncDBConnector
from .base import BaseAsyncNL2QDatasetLoader, GetSplitMixin


class Spider2SnowDatasetLoader(GetSplitMixin):
    name: ClassVar[str] = "spider2-snow"
    splits: ClassVar[list[str]] = ["dev"]

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

        # The default warehouse for Spider2 snowflake is "small" which allows for 16 concurrent queries
        self._dbms_semaphore = asyncio.Semaphore(16)

    def _load_column_descriptions(self) -> dict[tuple[str, str, str, str], str]:
        res = {}
        directory = os.path.join(self.directory, "resource", "databases")
        for db_name in os.listdir(directory):
            for schema_name in os.listdir(os.path.join(directory, db_name)):
                for table_file in os.listdir(os.path.join(directory, db_name, schema_name)):
                    if not table_file.endswith(".json"):
                        continue
                    table_name = table_file.replace(".json", "")
                    with open(os.path.join(directory, db_name, schema_name, table_file), "r") as f:
                        data = json.load(f)
                        for column, description in zip(data["column_names"], data["description"]):
                            res[(db_name, schema_name, table_name, column)] = description
        return res

    def get_database_names(self, split: str) -> list[str]:
        with open(os.path.join(self.directory, "spider2-snow.jsonl"), "r") as f:
            return list(dict.fromkeys([json.loads(line)["db_id"] for line in f]))

    async def get_tasks_async(self, split: str) -> list[NL2QTask]:
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
                        gold_sql = f.read()
                else:
                    gold_sql = None

                pattern = re.compile(rf"^{re.escape(item['instance_id'])}(_[a-z])?\.csv$")
                gold_exec_result_files = [file for file in all_gold_exec_result_files if re.match(pattern, file)]
                gold_exec_result_files = sorted(gold_exec_result_files)  # must load from a to z
                gold_exec_results = []
                for file in gold_exec_result_files:
                    with open(os.path.join(self.directory, "evaluation_suite", "gold", "exec_result", file), "r") as f:
                        gold_exec_results.append(pd.read_csv(f))

                tasks.append(
                    SimpleNL2QTask(
                        qid=item["instance_id"],
                        language="SnowflakeSQL",
                        db=item["db_id"],
                        question=item["instruction"],
                        evidence=evidence,
                        gold_queries=[
                            GoldQuery(id=f"GQRY-{i}", query=gold_sql, exec_result=ExecResult(df=df))
                            for i, df in enumerate(gold_exec_results)
                        ],
                        extra_info=eval_standard[item["instance_id"]],
                    )
                )

        return tasks

    async def get_databases_async(self, split: str, databases: list[str]) -> dict[str, BaseAsyncDBConnector]:
        """Get database connectors for the specified databases."""
        if split != "dev":
            raise ValueError(f"Split {split} not supported")

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
        for name in databases:
            db_conn = await SQLConnector.from_url_async(
                f"spider2-snow+{name}",
                name,
                "sync",
                f"{base_url}/{name}",
                max_concurrency_per_db=2,
                connect_args=connect_args,
            )
            schemas.append(db_conn.schema)

        # We set the per-db concurrency to 2 because there are 151 databases so we can have up to 151 x 2 = 302 concurrent connections
        db_connectors = [
            await SQLConnector.from_url_async(
                f"spider2-snow+{name}",
                name,
                "sync",
                f"{base_url}/{name}",
                max_concurrency_per_db=2,
                dbms_semaphore=self._dbms_semaphore,
                schema=schema,
                connect_args=connect_args,
            )
            for name, schema in zip(databases, schemas)
        ]

        column_descriptions = self._load_column_descriptions()
        for conn in db_connectors:
            for table in conn.schema.tables:
                table.name = table.name.upper()
                table.schema_name = table.schema_name.upper()  # type: ignore
                for column in table.columns:
                    column.description = column_descriptions.get(
                        (conn.schema.name, table.schema_name, table.name, column.name), None
                    )

        return {name: conn for name, conn in zip(databases, db_connectors)}
