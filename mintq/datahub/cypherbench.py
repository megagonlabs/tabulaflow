"""CypherBench text-to-Cypher benchmark (Neo4j property graphs).

Clone the Hugging Face dataset repo (see https://huggingface.co/datasets/megagonlabs/cypherbench)
into ``data/cypherbench`` so it contains ``train.json`` and ``test.json``.

Deploy graphs with the official Docker Compose files under the CypherBench repo
(``docker/docker-compose-train.yml`` and ``docker/docker-compose-test.yml``).
Default Bolt ports match those files when using ``localhost`` and the default
``neo4j`` / ``cypherbench`` credentials.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Any, ClassVar, Mapping

from mintq.datahub.base import dataset_registry
from mintq.db_connector import Neo4jConnector
from mintq.schema import GoldQuery, NL2QDataset, SimpleNL2QTask

# Official docker-compose port mapping: graph name -> host Bolt port (7687 in container).
_CYPHERBENCH_DEFAULT_PORTS: dict[str, int] = {
    "art": 15060,
    "biology": 15061,
    "company": 15062,
    "fictional_character": 15063,
    "flight_accident": 15064,
    "geography": 15065,
    "movie": 15066,
    "nba": 15067,
    "politics": 15068,
    "soccer": 15069,
    "terrorist_attack": 15070,
}

_CYPHERBENCH_TEST_GRAPHS: list[str] = [
    "company",
    "fictional_character",
    "flight_accident",
    "geography",
    "movie",
    "nba",
    "politics",
]

_CYPHERBENCH_TRAIN_GRAPHS: list[str] = [
    "art",
    "biology",
    "soccer",
    "terrorist_attack",
]

# (see ``https://github.com/megagonlabs/cypherbench/blob/main/cypherbench/baseline/zero_shot_nl2cypher.py``)
_CYPHERBENCH_DATASET_INSTRUCTIONS = """
- Translate the question to a **Cypher** query for the Neo4j property graph named in each task, using only the provided schema.
- Output the Cypher on a **single line**.
- Prefer **graph pattern matching** in the `MATCH` clause when possible.
- Avoid listing the same entity multiple times in the result rows; if several distinct entities share the same name, repeat that name as separate rows as needed.
- Do **not** return node objects; return entity **names** or **scalar properties** instead.
""".strip()


@dataset_registry.register
class CypherBenchDatasetLoader:
    name: ClassVar[str] = "cypherbench"
    splits: ClassVar[list[str]] = ["test", "train"]

    def __init__(
        self,
        directory: str = "data/cypherbench",
        neo4j_host: str = "localhost",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "cypherbench",
        graph_ports: Mapping[str, int] | None = None,
        max_concurrency_per_db: int = 4,
    ):
        self.directory = directory
        self.neo4j_host = neo4j_host
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self._graph_ports: dict[str, int] = dict(_CYPHERBENCH_DEFAULT_PORTS)
        if graph_ports:
            self._graph_ports.update(dict(graph_ports))
        self.max_concurrency_per_db = max_concurrency_per_db

    def _split_graphs(self, split: str) -> list[str]:
        if split == "test":
            return list(_CYPHERBENCH_TEST_GRAPHS)
        if split == "train":
            return list(_CYPHERBENCH_TRAIN_GRAPHS)
        raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

    def _task_file(self, split: str) -> str:
        return os.path.join(self.directory, f"{split}.json")

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")
        return self._split_graphs(split)

    def _bolt_url(self, graph: str) -> str:
        port = self._graph_ports[graph]
        return f"neo4j://{self.neo4j_host}:{port}"

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        path = self._task_file(split)
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"CypherBench tasks not found at {path!r}. "
                "Clone https://huggingface.co/datasets/megagonlabs/cypherbench into "
                f"{self.directory!r} (or pass directory=... to the loader)."
            )

        allowed = set(databases or self._split_graphs(split))
        tasks: list[SimpleNL2QTask] = []
        with open(path, encoding="utf-8") as f:
            raw: list[dict[str, Any]] = json.load(f)

        for item in raw:
            graph = item["graph"]
            if graph not in allowed:
                continue
            qid = item["qid"]
            extra: dict[str, Any] = {
                "cypherbench": {
                    "answer_json": item.get("answer_json"),
                    "from_template": item.get("from_template"),
                }
            }
            tasks.append(
                SimpleNL2QTask(
                    qid=qid,
                    db=graph,
                    question=item["nl_question"],
                    question_instructions=None,
                    dataset_instructions=_CYPHERBENCH_DATASET_INSTRUCTIONS,
                    gold_query=GoldQuery(query=item["gold_cypher"]),
                    extra_info=extra,
                )
            )
        return tasks

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> dict[str, Neo4jConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self._split_graphs(split)
        auth = (self.neo4j_user, self.neo4j_password)

        async def _one(graph: str) -> Neo4jConnector:
            if graph not in self._graph_ports:
                raise ValueError(
                    f"Unknown CypherBench graph {graph!r}. "
                    f"Known graphs: {sorted(self._graph_ports)}. "
                    "Override with graph_ports={{...}} if using custom ports."
                )
            return await Neo4jConnector.from_url_async(
                global_id=f"cypherbench+{graph}",
                url=self._bolt_url(graph),
                auth=auth,
                database=None,
                db_name=graph,
                read_only=True,
            )

        connectors = await asyncio.gather(*[_one(g) for g in databases])
        return dict(zip(databases, connectors, strict=True))

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset:
        dbs = databases or self._split_graphs(split)
        tasks = await self.get_tasks_async(split, dbs)
        if subsample_size is not None and tasks:
            k = min(subsample_size, len(tasks))
            tasks = random.Random(42).sample(tasks, k)
            dbs = sorted({t.db for t in tasks})
        db_connectors = await self.get_db_connectors_async(split, dbs)
        return NL2QDataset(
            name=self.name,
            split=split,
            databases=dbs,
            subsample_size=subsample_size,
            tasks=tasks,
            db_connectors=db_connectors,
        )
