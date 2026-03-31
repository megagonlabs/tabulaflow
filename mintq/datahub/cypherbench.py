"""CypherBench text-to-Cypher benchmark (Neo4j property graphs).

See https://huggingface.co/datasets/megagonlabs/cypherbench for the dataset.
Clone it into ``data/cypherbench`` (``train.json``, ``test.json``). Deploy graphs
with the official Docker Compose files in the CypherBench repo
(``docker/docker-compose-train.yml``, ``docker/docker-compose-test.yml``); default
Bolt host ports and ``neo4j`` / ``cypherbench`` credentials match those files.
"""

import asyncio
import json
import os
import random
from typing import Any, ClassVar, Mapping

from mintq.datahub.base import dataset_registry
from mintq.db_connector import Neo4jConnector
from mintq.schema import GoldQuery, NL2QDataset, SimpleNL2QTask

# Host Bolt port per graph (container listens on 7687). Matches official compose.
CYPHERBENCH_DEFAULT_GRAPH_PORTS: dict[str, int] = {
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

CYPHERBENCH_SPLIT_GRAPHS: dict[str, list[str]] = {
    "test": [
        "company",
        "fictional_character",
        "flight_accident",
        "geography",
        "movie",
        "nba",
        "politics",
    ],
    "train": ["art", "biology", "soccer", "terrorist_attack"],
}

# Mirrors CypherBench baseline ``NL2CYPHER_PROMPT_DEFAULT`` (``cypherbench/baseline/zero_shot_nl2cypher.py``).
CYPHERBENCH_DATASET_INSTRUCTIONS = """
- Translate the question to a **Cypher** query for the Neo4j property graph named in each task, using only the provided schema.
- Output the Cypher on a **single line**.
- Prefer **graph pattern matching** in the `MATCH` clause when possible.
- Avoid listing the same entity multiple times in the result rows; if several distinct entities share the same name, repeat that name as separate rows as needed.
- Do **not** return node objects; return entity **names** or **scalar properties** instead.
""".strip()


@dataset_registry.register
class CypherBenchDatasetLoader:
    """Loader for CypherBench (text-to-Cypher over Neo4j property graphs)."""

    name: ClassVar = "cypherbench"
    splits: ClassVar = ["test", "train"]

    def __init__(
        self,
        directory: str = "data/cypherbench",
        neo4j_host: str = "localhost",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "cypherbench",
        graph_ports: Mapping[str, int] | None = None,
    ):
        """Initializes the CypherBench dataset loader.

        Args:
            directory: Path containing ``train.json`` and ``test.json``.
            neo4j_host: Bolt host for deployed graphs.
            neo4j_user: Neo4j username.
            neo4j_password: Neo4j password.
            graph_ports: Optional overrides for graph name -> host Bolt port.
        """
        self.directory = directory
        self.neo4j_host = neo4j_host
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self._graph_ports: dict[str, int] = dict(CYPHERBENCH_DEFAULT_GRAPH_PORTS)
        if graph_ports:
            self._graph_ports.update(dict(graph_ports))

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")
        return list(CYPHERBENCH_SPLIT_GRAPHS[split])

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        path = os.path.join(self.directory, f"{split}.json")
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"CypherBench tasks not found at {path!r}. "
                "Clone https://huggingface.co/datasets/megagonlabs/cypherbench into "
                f"{self.directory!r} (or pass directory=... to the loader)."
            )

        databases = databases or self.get_databases(split)
        allowed = set(databases)
        with open(path, encoding="utf-8") as f:
            raw: list[dict[str, Any]] = json.load(f)

        return [
            SimpleNL2QTask(
                qid=item["qid"],
                db=item["graph"],
                question=item["nl_question"],
                question_instructions=None,
                dataset_instructions=CYPHERBENCH_DATASET_INSTRUCTIONS,
                gold_query=GoldQuery(query=item["gold_cypher"]),
                extra_info={
                    "cypherbench": {
                        "answer_json": item.get("answer_json"),
                        "from_template": item.get("from_template"),
                    }
                },
            )
            for item in raw
            if item["graph"] in allowed
        ]

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> dict[str, Neo4jConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        auth = (self.neo4j_user, self.neo4j_password)

        async def connect(graph: str) -> Neo4jConnector:
            if graph not in self._graph_ports:
                raise ValueError(
                    f"Unknown CypherBench graph {graph!r}. "
                    f"Known graphs: {sorted(self._graph_ports)}. "
                    "Override with graph_ports={{...}} if using custom ports."
                )
            url = f"neo4j://{self.neo4j_host}:{self._graph_ports[graph]}"
            return await Neo4jConnector.from_url_async(
                global_id=f"cypherbench+{graph}",
                url=url,
                auth=auth,
                database=None,
                db_name=graph,
                read_only=True,
            )

        connectors = await asyncio.gather(*[connect(g) for g in databases])
        return dict(zip(databases, connectors, strict=True))

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        dbs = databases or list(CYPHERBENCH_SPLIT_GRAPHS[split])
        tasks = await self.get_tasks_async(split, dbs)
        if subsample_size:
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
