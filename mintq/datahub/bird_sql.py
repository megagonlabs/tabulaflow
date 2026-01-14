import os
import json
import asyncio
import random
from typing import ClassVar
from datasets import load_dataset
from mintq.schema import SimpleNL2QTask, NL2QDataset, GoldQuery
from mintq.db_connector import SQLConnector
from mintq.datahub.base import dataset_registry


BIRD_DATASET_INSTRUCTIONS = """
- Do not concatenate columns in the results unless explicitly requested.
- If the question asks for a list of objects, return their names if available (e.g. for students), otherwise return their IDs (e.g. for transactions).
- The final query should not return additional columns that are not explicitly requested by the question.
  - For example, if the question only asks for the highest score but not the name of the student, the final query should not return the name of the student.
  - Similarly, if the question only asks for the student with the highest score but not the score, the final query should not return the score.
  - If the question requests a list of items sorted by a specific column, do not include the sorting column in the output unless it is specifically requested.
- If the question refers to the object with the maximum or minimum value, assume there is exactly one such object.
- Ensure that the columns in the output appear in the same order as they are mentioned in the question.
""".strip()


@dataset_registry.register
class BirdSQLDatasetLoader:
    name: ClassVar = "bird-sql"
    splits: ClassVar = ["train", "dev_20240627", "dev_20251106"]

    def __init__(
        self,
        directory: str = "data/BIRD-SQL",
        column_meaning_directory: str = "data/BIRD-SQL_column_meaning",
        max_concurrency: int = 16,
    ):
        self.directory = directory
        self.column_meaning_directory = column_meaning_directory
        self.max_concurrency = max_concurrency
        self._dbms_semaphore = asyncio.Semaphore(max_concurrency)

        self._task_files = {
            "train": os.path.join(self.directory, "train", "train.json"),
            "dev_20240627": os.path.join(self.directory, "dev_20240627", "dev.json"),
            "dev_20251106": os.path.join(self.directory, "dev_20251106", "dev.json"),
        }
        self._db_dirs = {
            "train": os.path.join(self.directory, "train", "train_databases"),
            "dev_20240627": os.path.join(self.directory, "dev_20240627", "dev_databases"),
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
          (1) They use syntax that is valid in native SQLite but not valid in sqlalchemy.
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

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        tasks = []
        with open(self._task_files[split], "r") as f:
            for i, item in enumerate(json.load(f)):
                if item["db_id"] in databases:
                    tasks.append(
                        SimpleNL2QTask(
                            qid=f"{self.name}_{split}_{i}",
                            language="SQLite",
                            db=item["db_id"],
                            question=item["question"],
                            question_instructions=item["evidence"],
                            gold_query=GoldQuery(query=self._fix_gold_query(item["SQL"])),
                            dataset_instructions=BIRD_DATASET_INSTRUCTIONS,
                            extra_info={"bird_sql": {"difficulty": item["difficulty"]}},
                        )
                    )
        return tasks

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        db_dir = self._db_dirs[split]
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"bird-sql+{name}",
                    db_name=name,
                    engine_type="async",
                    url=f"sqlite+aiosqlite:///{os.path.join(db_dir, name, f'{name}.sqlite')}",
                    max_concurrency_per_db=self.max_concurrency,
                    dbms_semaphore=self._dbms_semaphore,
                )
                for name in databases
            ]
        )
        canonical_split = "dev" if split.startswith("dev") else "train"
        with open(os.path.join(self.column_meaning_directory, f"{canonical_split}_column_meaning.json"), "r") as f:
            column_descriptions = {
                key: value.strip().strip("#").strip().replace("\n", " ") for key, value in json.load(f).items()
            }
        for conn in db_connectors:
            for table in conn.schema.tables:
                for column in table.columns:
                    column.description = column_descriptions.get(f"{conn.schema.name}|{table.name}|{column.name}", None)
        return {name: conn for name, conn in zip(databases, db_connectors)}

    def _ensure_dev_20251106_downloaded(self) -> None:
        path = os.path.join(self.directory, "dev_20251106")
        if not os.path.exists(path):
            os.makedirs(path)
            dataset = load_dataset("birdsql/bird_sql_dev_20251106")
            df = dataset["dev_20251106"].to_pandas()
            df.to_json(os.path.join(path, "dev.json"), orient="records", indent=2)

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset:
        if split == "dev_20251106":
            self._ensure_dev_20251106_downloaded()

        tasks = await self.get_tasks_async(split, databases)
        if subsample_size:
            tasks = random.Random(42).sample(tasks, subsample_size)
        db_connectors = await self.get_db_connectors_async(split, databases)
        return NL2QDataset(
            name=self.name,
            split=split,
            databases=databases,
            subsample_size=subsample_size,
            tasks=tasks,  # type: ignore
            db_connectors=db_connectors,
        )
