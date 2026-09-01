"""CypherBench text-to-Cypher benchmark (Neo4j property graphs).

Install it with ``tabulaflow benchmark download cypherbench``. Deploy graphs with
the installed official Docker Compose files; default Bolt host ports and
``neo4j`` / ``cypherbench`` credentials match those files.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, ClassVar, Mapping

from huggingface_hub import snapshot_download
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError

from tabulaflow.research.benchmarks.registry import dataset_registry, select_tasks, selected_databases
from tabulaflow.research.benchmarks.installation import BenchmarkInstallation, ProgressCallback, download_file
from tabulaflow.research.benchmarks.runtime import (
    BenchmarkRuntime,
    ensure_docker,
    run_command,
    wait_until_ready,
)
from tabulaflow.data import Neo4jConnector, Neo4jConnectorConfig
from tabulaflow.research.types import GoldQuery
from tabulaflow.research.types import NL2QDataset, SimpleNL2QTask

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
CYPHERBENCH_DATA_REVISION = "efdfde14c04fe174b4960544c1b1001530e2a178"
CYPHERBENCH_RUNTIME_REVISION = "94605181d12d9bc837f737a37b9d46471c2f3eff"


async def _fetch_cypherbench(destination: Path, progress: ProgressCallback) -> None:
    progress("Downloading benchmark data")
    await asyncio.to_thread(
        snapshot_download,
        repo_id="megagonlabs/cypherbench",
        repo_type="dataset",
        revision=CYPHERBENCH_DATA_REVISION,
        local_dir=destination,
    )
    runtime_files = (".env", "docker-compose-test.yml", "docker-compose-train.yml")
    progress("Downloading database runtime")
    await asyncio.gather(
        *[
            download_file(
                "https://raw.githubusercontent.com/megagonlabs/cypherbench/"
                f"{CYPHERBENCH_RUNTIME_REVISION}/docker/{filename}",
                destination / "docker" / filename,
            )
            for filename in runtime_files
        ]
    )
    for filename in runtime_files[1:]:
        path = destination / "docker" / filename
        path.write_text(path.read_text().replace("../benchmark/graphs/", "../graphs/"))


CYPHERBENCH_INSTALLATION = BenchmarkInstallation(
    name="cypherbench",
    required_paths=(
        "test.json",
        "train.json",
        *(f"graphs/simplekg/{graph}_simplekg.json" for graph in CYPHERBENCH_DEFAULT_GRAPH_PORTS),
        "docker/.env",
        "docker/docker-compose-test.yml",
        "docker/docker-compose-train.yml",
    ),
    fetch=_fetch_cypherbench,
)


async def _cypherbench_ready(split: str) -> bool:
    async def graph_ready(graph: str) -> bool:
        driver = AsyncGraphDatabase.driver(
            f"neo4j://localhost:{CYPHERBENCH_DEFAULT_GRAPH_PORTS[graph]}",
            auth=("neo4j", "cypherbench"),
            connection_timeout=2,
        )
        try:
            await driver.verify_connectivity()
            return True
        except (Neo4jError, OSError, asyncio.TimeoutError):
            return False
        finally:
            await driver.close()

    return all(await asyncio.gather(*(graph_ready(graph) for graph in CYPHERBENCH_SPLIT_GRAPHS[split])))


async def _start_cypherbench(split: str | None, progress: ProgressCallback) -> None:
    assert split is not None
    await ensure_docker()
    progress(f"Starting CypherBench {split} databases")
    docker_dir = CYPHERBENCH_INSTALLATION.directory / "docker"
    await run_command(
        "docker",
        "compose",
        "--project-name",
        f"tabulaflow-cypherbench-{split}",
        "--env-file",
        ".env",
        "-f",
        f"docker-compose-{split}.yml",
        "up",
        "-d",
        cwd=docker_dir,
    )
    progress("Waiting for Neo4j")
    await wait_until_ready(lambda: _cypherbench_ready(split), f"CypherBench {split} databases")


async def _stop_cypherbench(split: str | None, progress: ProgressCallback) -> None:
    assert split is not None
    await ensure_docker()
    progress(f"Stopping CypherBench {split} databases")
    await run_command(
        "docker",
        "compose",
        "--project-name",
        f"tabulaflow-cypherbench-{split}",
        "--env-file",
        ".env",
        "-f",
        f"docker-compose-{split}.yml",
        "stop",
        cwd=CYPHERBENCH_INSTALLATION.directory / "docker",
    )


CYPHERBENCH_RUNTIME = BenchmarkRuntime(
    start_action=_start_cypherbench,
    stop_action=_stop_cypherbench,
    splits=("test", "train"),
    default_split="test",
)


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

    name: ClassVar[str] = "cypherbench"
    splits: ClassVar[list[str]] = ["test", "train"]
    installation: ClassVar[BenchmarkInstallation] = CYPHERBENCH_INSTALLATION
    runtime: ClassVar[BenchmarkRuntime] = CYPHERBENCH_RUNTIME
    default_metrics: ClassVar[list[str]] = [
        "cypherbench_ex",
        "simple_ex",
        "psjs",
        "executable",
        "gold_executable",
        "gold_result_not_empty",
        "pred_success",
    ]

    def __init__(
        self,
        directory: str | None = None,
        neo4j_host: str = "localhost",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "cypherbench",
        graph_ports: Mapping[str, int] | None = None,
        connector_config: Neo4jConnectorConfig | None = None,
    ):
        """Initializes the CypherBench dataset loader.

        Args:
            directory: Path containing ``train.json`` and ``test.json``.
            neo4j_host: Bolt host for deployed graphs.
            neo4j_user: Neo4j username.
            neo4j_password: Neo4j password.
            graph_ports: Optional overrides for graph name -> host Bolt port.
        """
        if directory is None:
            self.installation.require()
        self.directory = str(self.installation.directory if directory is None else directory)
        self.neo4j_host = neo4j_host
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.connector_config = Neo4jConnectorConfig() if connector_config is None else connector_config
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
                "Run `tabulaflow benchmark download cypherbench` or pass a valid directory to the loader."
            )

        databases = self.get_databases(split) if databases is None else databases
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

        databases = self.get_databases(split) if databases is None else databases
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
                config=self.connector_config,
            )

        connectors = await asyncio.gather(*[connect(g) for g in databases])
        return dict(zip(databases, connectors, strict=True))

    async def get_split_async(
        self,
        split: str,
        databases: list[str] | None = None,
        subsample_size: int | None = None,
        qids: list[str] | None = None,
    ) -> NL2QDataset:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        dbs = list(CYPHERBENCH_SPLIT_GRAPHS[split]) if databases is None else databases
        tasks = select_tasks(await self.get_tasks_async(split, dbs), qids, subsample_size)
        dbs = selected_databases(tasks)
        db_connectors = await self.get_db_connectors_async(split, dbs)
        return NL2QDataset(
            name=self.name,
            split=split,
            databases=dbs,
            subsample_size=subsample_size,
            tasks=tasks,  # type: ignore
            db_connectors=db_connectors,
        )
