import os
import json
import asyncio
import shutil
from pathlib import Path
from typing import Any, ClassVar
from tabulaflow.research.types import GoldQuery
from tabulaflow.research.types import SimpleNL2QTask, NL2QDataset
from tabulaflow.data import SQLConnector, SQLConnectorConfig
from tabulaflow.research.benchmarks.registry import dataset_registry, select_tasks, selected_databases
from tabulaflow.research.benchmarks.installation import (
    BenchmarkInstallation,
    ProgressCallback,
    download_github_directory,
    download_google_drive,
    extract_zip,
)
from tabulaflow.research.benchmarks.runtime import (
    BenchmarkRuntime,
    BenchmarkRuntimeError,
    ensure_docker,
    run_command,
    wait_until_ready,
)

BEAVER_REVISION = "bccdeb664d27b89ac296133b46553b8113912454"
BEAVER_DATABASES = {
    "dw": "https://drive.google.com/uc?id=19SXkvFtrAVCL-hRgRsQ9Yt5YZQP8ZYQy",
    "nw": "https://drive.google.com/uc?id=1KJWdSGJ67DCwuxcWepZM2jJXXTphTnuw",
}


def _install_beaver_database(archive: Path, destination: Path) -> None:
    extracted = archive.with_suffix("")
    if extracted.exists():
        shutil.rmtree(extracted)
    extract_zip(archive, extracted)
    destination.mkdir(parents=True, exist_ok=True)
    for sql_file in extracted.rglob("*.sql"):
        shutil.copy2(sql_file, destination / sql_file.name)
    shutil.rmtree(extracted)


async def _fetch_beaver(destination: Path, progress: ProgressCallback) -> None:
    progress("Downloading Beaver")
    await download_github_directory("peterbaile/beaver", BEAVER_REVISION, "", destination)
    for name, url in BEAVER_DATABASES.items():
        database_dir = destination / name
        archive = destination / f".{name}.zip"
        if any(database_dir.glob("*.sql")) and not archive.exists():
            continue
        progress(f"Downloading Beaver {name.upper()} database")
        if not archive.exists():
            await download_google_drive(url, archive)
        await asyncio.to_thread(_install_beaver_database, archive, database_dir)
        archive.unlink()


BEAVER_INSTALLATION = BenchmarkInstallation(
    name="beaver",
    required_paths=("dev_dw.json", "dev_nw.json", "dw", "nw"),
    fetch=_fetch_beaver,
)
BEAVER_CONTAINERS = {
    "dw": ("tabulaflow-beaver-dw", 3311),
    "nw": ("tabulaflow-beaver-nw", 3312),
}


async def _container_exists(name: str) -> bool:
    output = await run_command("docker", "ps", "-a", "--format", "{{.Names}}")
    return name in output.splitlines()


async def _beaver_ready(split: str | None) -> bool:
    async def database_ready(container: str) -> bool:
        try:
            await run_command("docker", "exec", container, "mysqladmin", "ping", "-uroot", "-proot", "--silent")
            return True
        except BenchmarkRuntimeError:
            return False

    return all(await asyncio.gather(*(database_ready(container) for container, _ in BEAVER_CONTAINERS.values())))


async def _start_beaver(split: str | None, progress: ProgressCallback) -> None:
    await ensure_docker()
    progress("Starting Beaver databases")
    existing = []
    for name, (container, port) in BEAVER_CONTAINERS.items():
        if await _container_exists(container):
            existing.append(container)
            continue
        await run_command(
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "-p",
            f"{port}:3306",
            "-e",
            "MYSQL_ROOT_PASSWORD=root",
            "-v",
            f"tabulaflow-beaver-{name}:/var/lib/mysql",
            "-v",
            f"{BEAVER_INSTALLATION.directory / name}:/docker-entrypoint-initdb.d:ro",
            "mysql:8.0",
            "--lower-case-table-names=1",
        )
    if existing:
        await run_command("docker", "start", *existing)
    progress("Waiting for MySQL")
    await wait_until_ready(lambda: _beaver_ready(None), "Beaver databases")


async def _stop_beaver(split: str | None, progress: ProgressCallback) -> None:
    await ensure_docker()
    progress("Stopping Beaver databases")
    existing = [container for container, _ in BEAVER_CONTAINERS.values() if await _container_exists(container)]
    if existing:
        await run_command("docker", "stop", *existing)


BEAVER_RUNTIME = BenchmarkRuntime(
    start_action=_start_beaver,
    stop_action=_stop_beaver,
    ready_action=_beaver_ready,
)


@dataset_registry.register
class BeaverDatasetLoader:
    name: ClassVar[str] = "beaver"
    splits: ClassVar[list[str]] = ["test"]
    installation: ClassVar[BenchmarkInstallation] = BEAVER_INSTALLATION
    runtime: ClassVar[BenchmarkRuntime] = BEAVER_RUNTIME
    default_metrics: ClassVar[list[str]] = [
        "simple_ex",
        "executable",
        "gold_executable",
        "gold_result_not_empty",
        "pred_success",
    ]

    def __init__(
        self,
        directory: str | None = None,
        dw_port: int = 3311,
        nw_port: int = 3312,
        connector_config: SQLConnectorConfig | None = None,
    ):
        if directory is None:
            self.installation.require()
        self.directory = str(self.installation.directory if directory is None else directory)
        self.dw_dbms_port = dw_port
        self.nw_dbms_port = nw_port
        self.connector_config = SQLConnectorConfig() if connector_config is None else connector_config
        self._data: dict[Any, NL2QDataset] = {}

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        return [
            "dw",
            "csail_stata_cinder",
            "csail_stata_neutron",
            "csail_stata_glance",
            "csail_stata_nova",
            "keystone",
        ]

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = self.get_databases(split) if databases is None else databases
        tasks = []
        for file in ["dev_dw.json", "dev_nw.json"]:
            source = file.removesuffix(".json")
            with open(os.path.join(self.directory, file), "r") as f:
                data = json.load(f)

            for i, item in enumerate(data):
                if item["db_id"] in databases:
                    tasks.append(
                        SimpleNL2QTask(
                            qid=f"{self.name}_{split}_{source}_{i}",
                            db=item["db_id"],
                            question=item["question"],
                            document=None,
                            gold_query=GoldQuery(query=item["sql"]),
                        )
                    )
        return tasks

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = self.get_databases(split) if databases is None else databases
        urls = {
            db: f"mysql+asyncmy://root:root@localhost:{self.dw_dbms_port if db == 'dw' else self.nw_dbms_port}/{db}"
            for db in databases
        }
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    url,
                    global_id=f"beaver+{name}",
                    display_name=name,
                    config=self.connector_config.model_copy(update={"max_query_concurrency": 16}),
                )
                for name, url in urls.items()
            ]
        )
        return {name: conn for name, conn in zip(databases, db_connectors)}

    async def get_split_async(
        self,
        split: str,
        databases: list[str] | None = None,
        subsample_size: int | None = None,
        qids: list[str] | None = None,
    ) -> NL2QDataset:
        tasks = select_tasks(await self.get_tasks_async(split, databases), qids, subsample_size)
        databases = selected_databases(tasks)
        db_connectors = await self.get_db_connectors_async(split, databases)
        return NL2QDataset(
            name=self.name,
            split=split,
            databases=databases,
            subsample_size=subsample_size,
            tasks=tasks,  # type: ignore
            db_connectors=db_connectors,
        )
