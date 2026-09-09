import os
import json
import asyncio
import shutil
from pathlib import Path
from typing import ClassVar, Literal

from datasets import load_dataset

from tabulaflow.research.types import GoldQuery
from tabulaflow.research.types import SimpleNL2QTask, NL2QDataset
from tabulaflow.data import SQLConnector, SQLConnectorConfig
from tabulaflow.research.benchmarks.registry import dataset_registry, select_tasks, selected_databases
from tabulaflow.research.benchmarks.installation import (
    BenchmarkInstallation,
    BenchmarkInstallationError,
    ProgressCallback,
    copy_directory_contents,
    download_file,
    download_zip,
    extract_zip,
)

BIRD_TRAIN_URL = "https://bird-bench.oss-cn-beijing.aliyuncs.com/train.zip"
BIRD_DEV_URL = "https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip"
BIRD_UPDATED_DEV_REVISION = "3c11fb193e5439b338e23677fa0aae11e8b85db9"
BIRD_COLUMN_MEANING_REVISION = "80f82b32ce6a7b80a21b9ad705c2539549ddd431"
BIRD_COLUMN_MEANING_URLS = {
    "dev_column_meaning.json": (
        f"https://raw.githubusercontent.com/quge2023/TA-SQL/{BIRD_COLUMN_MEANING_REVISION}/outputs/column_meaning.json"
    ),
    "train_column_meaning.json": (
        "https://raw.githubusercontent.com/quge2023/TA-SQL/"
        f"{BIRD_COLUMN_MEANING_REVISION}/data/train_column_meaning.json"
    ),
}


async def _fetch_bird_archive(destination: Path, name: str, url: str, task_file: str, database_dir: str) -> None:
    target = destination / name
    if (target / task_file).is_file() and (target / database_dir).is_dir():
        return
    archive = destination / f".{name}.zip"
    extracted = destination / f".{name}"
    await download_zip(url, archive)
    if extracted.exists():
        shutil.rmtree(extracted)
    await asyncio.to_thread(extract_zip, archive, extracted)
    matches = [
        path.parent
        for path in extracted.rglob(task_file)
        if (path.parent / database_dir).is_dir() or (path.parent / f"{database_dir}.zip").is_file()
    ]
    if len(matches) != 1:
        raise BenchmarkInstallationError(f"could not find one {task_file} and {database_dir} pair in {archive}")
    await asyncio.to_thread(copy_directory_contents, matches[0], target)
    database_archive = target / f"{database_dir}.zip"
    if database_archive.is_file():
        await asyncio.to_thread(extract_zip, database_archive, target / database_dir)
        database_archive.unlink()
        nested_database_dir = target / database_dir / database_dir
        if nested_database_dir.is_dir():
            await asyncio.to_thread(copy_directory_contents, nested_database_dir, target / database_dir)
            shutil.rmtree(nested_database_dir)
    archive.unlink()
    shutil.rmtree(extracted)


async def _fetch_bird_sql(destination: Path, progress: ProgressCallback) -> None:
    progress("Downloading BIRD-SQL train data")
    await _fetch_bird_archive(destination, "train", BIRD_TRAIN_URL, "train.json", "train_databases")
    progress("Downloading BIRD-SQL development data")
    await _fetch_bird_archive(destination, "dev_20240627", BIRD_DEV_URL, "dev.json", "dev_databases")
    progress("Downloading updated development annotations")

    def download_updated_dev() -> None:
        path = destination / "dev_20251106" / "dev.json"
        if path.is_file():
            return
        dataset = load_dataset("birdsql/bird_sql_dev_20251106", revision=BIRD_UPDATED_DEV_REVISION)
        path.parent.mkdir(parents=True, exist_ok=True)
        dataset["dev_20251106"].to_pandas().to_json(path, orient="records", indent=2)

    await asyncio.to_thread(download_updated_dev)
    progress("Downloading column descriptions")
    column_meaning_dir = destination / "column_meaning"
    column_meaning_dir.mkdir(exist_ok=True)
    await asyncio.gather(
        *[download_file(url, column_meaning_dir / name) for name, url in BIRD_COLUMN_MEANING_URLS.items()]
    )


BIRD_DATASET_INSTRUCTIONS = """
- **Strictly Follow Hints:**
  - If the user specifies a particular computation formula or requires using a specific column, follow those instructions.
- **SELECT Clause:**
  - In the final SELECT clause only return explicitly requested columns.
  - If the question asks for a set of entities, return their names if available (e.g. for students), otherwise return their IDs (e.g. for transactions).
  - Ensure that the SELECT columns appear in the same order as they are mentioned in the question.
  - Examples:
    - If the question asks for a maximum value, do not include the entity that attains it.
      Question: "What is the highest score?" Return columns: ["highest score"] (exclude the student).
    - If the question asks for the entity that attains a maximum value, do not include the value itself.
        Question: "Which student has the highest score?" Return columns: ["student name or id"] (exclude the score).
    - If the question asks for attributes of a set of entities, do not include the entities themselves.
        Question: "What are the birthdates of students?" Return columns: ["birthdate"] (exclude the student).
    - If the question asks for a list of items ordered by a specific attribute, do not include the ordering attribute.
        Question: "Who are the top 3 students by score?" Return columns: ["student name or id"] (exclude the score).
- **Yes/No Answers:**
  - Binary information (e.g. "Whether ...") that does not directly corresponds to a database column should be represented as values "YES" or "NO".
- **No String Concatenation:**
  - Do not concatenate strings in the results unless explicitly requested. In particular, do not combine first and last names into a single column.
- **Preserve Data Shape:**
  - When returning a list of records (e.g., dates) from multiple rows, maintain one row per record.
  - When returning columns that represent similar concepts, keep them as separate columns and do not merge or union them into a single column.
- **Percentage Values:**
    - Do not round percentage values unless explicitly requested.
    - If the question specifies * 1.0 or * 100.0, follow those instructions. 
    - If the question does not specified, percentage values should be multiplied by 100 by default, while rates or ratios should not be multiplied by 100.
    - When multiplying by 100.0, you must apply it to the numerator rather than the denominator, regardless of the formula in question hints.
- **Integer Division vs Decimal Division:**
  - SQLite uses integer division when both operands are integers (e.g., `5 / 2 = 2`, not `2.5`).
  - To get decimal results, cast at least one operand to REAL: `CAST(a AS REAL) / b`.
- **Rounding:**
  - Use ROUND() instead of printf() to round percentage values, since printf returns STRING instead of FLOAT.
- **DISTINCT Keyword:**
  - Use `SELECT DISTINCT` when the question requires unique values (e.g., IDs, URLs). 
  - Refer to column statistics ("Value Statics") to determine if `DISTINCT` is necessary.
- **Column Selection:**
  - Carefully analyze column descriptions and hints to choose the correct column when similar columns exist across tables.
- **JOIN Preference:**
  - Prioritize `INNER JOIN` over nested `SELECT` statements.
- **No Ties in Highest or Lowest Entity:**
  - When the question asks for the entities with the highest or lowest value, assume no ties exist.
  - Always prioritize using `[JOIN ...] [GROUP BY ...] ORDER BY ... LIMIT N` over a nested `WHERE column = (SELECT MAX(column) FROM ...)`.
- **SQLite Functions Only:**
  - Use only functions available in SQLite.
- **Date Processing:**
  - Utilize `STRFTIME()` for date manipulation (e.g., `STRFTIME('%Y', SOMETIME)` to extract the year).
- **AND vs OR Ambiguity:**
  - The word "and" can be ambiguous as it can be interpreted as a logical AND or a UNION/OR.
    In such cases, prioritize the logical AND interpretation by default, but when there are no matching entities, try the UNION/OR interpretation.
  - Example: "Entities with A and B" or "Entities that are A and B" by default means entities that satisfy both condition A and condition B simultaneously.
- **No Empty Results:**
  - The correct SQL query must return at least one row. If your query returns empty results, it is likely incorrect or the question may require a different interpretation.
""".strip()


@dataset_registry.register
class BirdSQLDatasetLoader:
    name: ClassVar[str] = "bird-sql"
    splits: ClassVar[list[str]] = ["dev", "dev_20251106", "train"]
    installation: ClassVar[BenchmarkInstallation] = BenchmarkInstallation(
        name=name,
        required_paths=(
            "dev_20240627/dev.json",
            "dev_20240627/dev_databases",
            "dev_20251106/dev.json",
            "train/train.json",
            "train/train_databases",
            "column_meaning/dev_column_meaning.json",
            "column_meaning/train_column_meaning.json",
        ),
        fetch=_fetch_bird_sql,
    )
    default_metrics: ClassVar[list[str]] = [
        "bird_sql_ex",
        "simple_ex",
        "bird_sql_ex_soft",
        "executable",
        "gold_executable",
        "gold_result_not_empty",
        "pred_success",
        "raw_pred_bird_sql_ex",
        "raw_pred_simple_ex",
        "schema_linking_stats",
    ]

    def __init__(
        self,
        directory: str | None = None,
        column_meaning_directory: str | None = None,
        max_concurrency: int = 16,
        connector_config: SQLConnectorConfig | None = None,
    ):
        if directory is None:
            self.installation.require()
        default_directory = self.installation.directory
        self.directory = str(default_directory if directory is None else directory)
        self.column_meaning_directory = str(
            default_directory / "column_meaning" if column_meaning_directory is None else column_meaning_directory
        )
        self.max_concurrency = max_concurrency
        self.connector_config = (
            SQLConnectorConfig(schema_cache_mode="read_write") if connector_config is None else connector_config
        )
        self._dbms_semaphore = asyncio.Semaphore(max_concurrency)

        self._task_files = {
            "train": os.path.join(self.directory, "train", "train.json"),
            "dev": os.path.join(self.directory, "dev_20240627", "dev.json"),
            "dev_20251106": os.path.join(self.directory, "dev_20251106", "dev.json"),
        }
        self._db_dirs = {
            "train": os.path.join(self.directory, "train", "train_databases"),
            "dev": os.path.join(self.directory, "dev_20240627", "dev_databases"),
            "dev_20251106": os.path.join(self.directory, "dev_20240627", "dev_databases"),
        }

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        with open(self._task_files[split], "r") as f:
            return list(dict.fromkeys([item["db_id"] for item in json.load(f)]))

    @staticmethod
    def _fix_gold_query(query: str) -> str:
        """
        In BIRD-SQL, a few gold queries are not executable in our library because:
          (1) They use syntax that is valid in native sqlite but not valid in sqlalchemy.
          (2) They are inefficient and exceed the execution time limit (default is 90 seconds).
        We rewrite them to an equivalent form that is valid in sqlalchemy and within the execution time limit.
        """

        # sqlalchemy treats :__ as a parameter
        if "LIKE '_:%:__.___'" in query:
            query = query.replace("LIKE '_:%:__.___'", "LIKE '_:%' || ':' || '__' || '.___'")

        #  The original query takes 4 minutes to execute, our rewrite takes 2.59 seconds (qid: bird-sql_dev_20251106_1131)
        if (
            query
            == "SELECT AVG(T1.height) FROM Player AS T1 INNER JOIN Match AS T2 ON T1.player_api_id IN (T2.home_player_1, T2.home_player_2, T2.home_player_3, T2.home_player_4, T2.home_player_5, T2.home_player_6, T2.home_player_7, T2.home_player_8, T2.home_player_9, T2.home_player_10, T2.home_player_11, T2.away_player_1, T2.away_player_2, T2.away_player_3, T2.away_player_4, T2.away_player_5, T2.away_player_6, T2.away_player_7, T2.away_player_8, T2.away_player_9, T2.away_player_10, T2.away_player_11) INNER JOIN Country AS T3 ON T2.country_id = T3.id WHERE T3.name = 'Italy'"
        ):
            query = """SELECT AVG(p.height) AS avg_height
FROM Player p
JOIN (
    SELECT home_player_1 AS player_api_id, country_id FROM Match
    UNION ALL SELECT home_player_2, country_id FROM Match
    UNION ALL SELECT home_player_3, country_id FROM Match
    UNION ALL SELECT home_player_4, country_id FROM Match
    UNION ALL SELECT home_player_5, country_id FROM Match
    UNION ALL SELECT home_player_6, country_id FROM Match
    UNION ALL SELECT home_player_7, country_id FROM Match
    UNION ALL SELECT home_player_8, country_id FROM Match
    UNION ALL SELECT home_player_9, country_id FROM Match
    UNION ALL SELECT home_player_10, country_id FROM Match
    UNION ALL SELECT home_player_11, country_id FROM Match
    UNION ALL SELECT away_player_1, country_id FROM Match
    UNION ALL SELECT away_player_2, country_id FROM Match
    UNION ALL SELECT away_player_3, country_id FROM Match
    UNION ALL SELECT away_player_4, country_id FROM Match
    UNION ALL SELECT away_player_5, country_id FROM Match
    UNION ALL SELECT away_player_6, country_id FROM Match
    UNION ALL SELECT away_player_7, country_id FROM Match
    UNION ALL SELECT away_player_8, country_id FROM Match
    UNION ALL SELECT away_player_9, country_id FROM Match
    UNION ALL SELECT away_player_10, country_id FROM Match
    UNION ALL SELECT away_player_11, country_id FROM Match
) mp ON mp.player_api_id = p.player_api_id
JOIN Country c ON c.id = mp.country_id
WHERE c.name = 'Italy';"""

        # The original query is invalid in sqlalchemy as it uses HAVING without GROUP BY (qid: bird-sql_dev_20251106_196)
        if "WHERE \n    cac.label = '-'\nHAVING \n    COUNT(DISTINCT cac.molecule_id) > 0" in query:
            query = query.replace(
                "WHERE \n    cac.label = '-'\nHAVING \n    COUNT(DISTINCT cac.molecule_id) > 0",
                "WHERE \n    cac.label = '-'\nGROUP BY '1'\nHAVING \n    COUNT(DISTINCT cac.molecule_id) > 0",
            )
        return query

    async def get_tasks_async(
        self,
        split: str,
        databases: list[str] | None = None,
        difficulty: str | Literal["simple", "moderate", "challenging"] | None = None,
    ) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = self.get_databases(split) if databases is None else databases
        tasks = []
        with open(self._task_files[split], "r") as f:
            for i, item in enumerate(json.load(f)):
                if item["db_id"] not in databases:
                    continue
                if difficulty is not None:
                    if "difficulty" not in item:
                        raise ValueError(f"BIRD-SQL split {split!r} does not provide difficulty labels")
                    if item["difficulty"] != difficulty:
                        continue
                tasks.append(
                    SimpleNL2QTask(
                        qid=f"{self.name}_{split}_{i}",
                        db=item["db_id"],
                        question=item["question"],
                        question_instructions=item["evidence"],
                        gold_query=GoldQuery(query=self._fix_gold_query(item["SQL"])),
                        dataset_instructions=BIRD_DATASET_INSTRUCTIONS,
                        extra_info={"bird_sql": {"difficulty": item["difficulty"]}} if "difficulty" in item else {},
                    )
                )
        return tasks

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = self.get_databases(split) if databases is None else databases
        db_dir = self._db_dirs[split]
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"bird-sql+{name}",
                    url=f"sqlite+aiosqlite:///{os.path.join(db_dir, name, f'{name}.sqlite')}",
                    display_name=name,
                    dbms_semaphore=self._dbms_semaphore,
                    config=self.connector_config.model_copy(update={"max_query_concurrency": self.max_concurrency}),
                )
                for name in databases
            ]
        )
        canonical_split = "dev" if split.startswith("dev") else "train"
        with open(os.path.join(self.column_meaning_directory, f"{canonical_split}_column_meaning.json"), "r") as f:
            column_descriptions = {
                key: value.strip().strip("#").strip().replace("\n", " ") for key, value in json.load(f).items()
            }
        for name, conn in zip(databases, db_connectors, strict=True):
            for table in conn.schema.tables:
                for column in table.columns:
                    column.description = column_descriptions.get(f"{name}|{table.name}|{column.name}", None)
        return {name: conn for name, conn in zip(databases, db_connectors)}

    async def get_split_async(
        self,
        split: str,
        databases: list[str] | None = None,
        subsample_size: int | None = None,
        qids: list[str] | None = None,
        difficulty: str | Literal["simple", "moderate", "challenging"] | None = None,
    ) -> NL2QDataset:
        tasks = select_tasks(
            await self.get_tasks_async(split, databases, difficulty=difficulty),
            qids,
            subsample_size,
        )
        databases = selected_databases(tasks)
        db_connectors = await self.get_db_connectors_async(split, databases)
        return NL2QDataset(
            name=self.name,
            split=split,
            databases=databases,
            subsample_size=subsample_size,
            dataset_extra_kwargs={"difficulty": difficulty} if difficulty else {},
            tasks=tasks,  # type: ignore
            db_connectors=db_connectors,
        )
