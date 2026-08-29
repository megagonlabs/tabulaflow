import os
import asyncio
import random
import json
import copy
from typing import ClassVar
from tabulaflow.research.types import AmbigNL2QTask, NL2QDataset
from tabulaflow.data import SQLConnector, SQLConnectorConfig
from tabulaflow.research.benchmarks.registry import dataset_registry

ARCS_DATASET_INSTRUCTIONS = """
- Follow these requirements when writing SQL. When disambiguating, do not consider these as ambiguities:
  - If the question asks for a list of objects, return their names if available (e.g. for students), otherwise return their IDs (e.g. for transactions).
  - You may include additional relevant columns that are mentioned in the question, even if they are not explicitly requested in the output.
  - Do not concatenate columns in the results unless explicitly requested.
  - For percentage values, don't multiply by 100.
  - Rounding is not needed for numerical values.
  - If the question asks for the object that achieves the maximum/minimum value, if there is a tie, return all tied objects.
""".strip()


ARCS_TAXONOMY = """
- In this dataset, there are two dimensions of ambiguity:
  I. Linguistic Dimension:
    - Semantic Ambiguity / Vagueness
      Definition: Words or phrases have multiple meanings or unclear thresholds.
    - Syntactic Ambiguity
      Definition: The question has multiple syntactic parses.
  II. Database Dimension:
    - Column Ambiguity
      Definition: A term in the question can map to multiple possible columns in the schema.
    - Table Ambiguity
      Definition: A referenced entity can map to more than one table in the database.
    - Value Ambiguity
      Definition: Query terms can match multiple values in a column, or describe vague concepts without clear boundaries.
    - Computation Ambiguity
      Definition: Required operations or metrics can be computed in multiple legitimate ways, producing distinct results.

- Therefore, the ambiguity point in the question is one of the following eight types:

1. Semantic + Column Ambiguity
   Example:
     DB: Product(id, name, retail_price, manufacture_price, tax)
     Question: “List the prices of all products”
     Possible interpretations:
       - Retail price
       - Manufacture price
       - Retail price after tax

2. Semantic + Table Ambiguity
   Example:
     DB: Singer(name), Dancer(name), Venue(id, name), PerformAt(artist_name, venue_id)
     Question: “Compute the number of performers who have performed at X venue”
     Possible interpretations:
       - Performers only from Singer table
       - Performers only from Dancer table
       - Both singers and dancers as performers

3. Semantic + Value Ambiguity
   Example:
     DB: Employee(id, name, salary, rating, work_hour)
     Question: “List all employees with high salary”
     Possible interpretations:
       - The threshold for high salary is unclear

4. Semantic + Computation Ambiguity
   Example:
     DB: Employee(id, name, base_salary, stock, benefit)
     Question: “Compute the income for each employee”
     Possible interpretations:
       - Total compensation (salary + stock + benefits)
       - Base salary only
       - Adjusted after-tax income

5. Syntactic + Column Ambiguity
   Example:
     DB: Product(id, name, max_rating, max_price, price)
     Question: “List the max rating and price among all products”
     Possible interpretations:
       - max_rating column + price column
       - max_rating column + max_price column

6. Syntactic + Table Ambiguity
   Example:
     DB: 2025_jan, 2024_jan, ...
     Question: “List orders in January 2025 or 2024”
     Possible interpretations:
       - Only January tables for this and last year (2025_jan, 2024_jan)
       - This January plus all tables from last year (2025_jan, 2024_dec … 2024_jan)

7. Syntactic + Value Ambiguity
   Example:
     DB: Order(id, date, ...)
     Question: “List orders in January 2025 or 2024”
     Possible interpretations:
       - January 2025 or January 2024
       - January 2025 or the entire 2024

8. Syntactic + Computation Ambiguity
   Example:
     DB: Employee(id, name, computer_type, os)
     Question: “Show IT staff who have desktops or laptops with Linux”
     Possible interpretations:
       - Desktops (any OS) OR laptops with Linux
       - Desktops with Linux OR laptops with Linux
""".strip()


@dataset_registry.register
class ARCSDatasetLoader:
    name: ClassVar[str] = "arcs"
    splits: ClassVar[list[str]] = ["test", "test_unsampled"]
    default_metrics: ClassVar[list[str]] = [
        "simple_ex",
        "executable",
        "gold_executable",
        "gold_result_not_empty",
        "pred_success",
        "ambig_point_stats",
        "gold_ambig_point_stats",
        "found_one",
    ]

    def __init__(
        self,
        directory: str = "data/ARCS/",
        column_meaning_directory: str = "data/BIRD-SQL_column_meaning",
        max_concurrency: int = 16,
        include_taxonomy: bool = False,
        connector_config: SQLConnectorConfig | None = None,
    ):
        self.directory = directory
        self.column_meaning_directory = column_meaning_directory
        self.max_concurrency = max_concurrency
        self.include_taxonomy = include_taxonomy
        self.connector_config = SQLConnectorConfig() if connector_config is None else connector_config

        self._dbms_semaphore = asyncio.Semaphore(max_concurrency)

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        return [
            "retails",
            "professional_basketball",
            "github_repos",
            "financial",
            "codebase_community",
            "student_club",
        ]

    def _upsample_tasks(self, tasks: list[AmbigNL2QTask]) -> list[AmbigNL2QTask]:
        with open(os.path.join(self.directory, "tasks", "tasks_gold_intended_query_ids.json"), "r") as f:
            qid_to_gold_query_ids = json.load(f)

        res = []
        for task in tasks:
            for i, gq_id in enumerate(qid_to_gold_query_ids[task.qid]):
                new_task = copy.deepcopy(task)
                new_task.qid = f"{task.qid}-{i}"
                new_task.gold_intended_query_id = gq_id
                ap_id_to_interpretation_idx = dict([part.split(".") for part in gq_id.split("-")[1:]])
                for ap in new_task.gold_ambiguity_points:
                    if ap.type == "finite":
                        ap.intended_interpretation_idx = int(ap_id_to_interpretation_idx[ap.id])
                res.append(new_task)
        return res

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[AmbigNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        if self.include_taxonomy:
            dataset_instructions = ARCS_DATASET_INSTRUCTIONS + "\n" + ARCS_TAXONOMY
        else:
            dataset_instructions = ARCS_DATASET_INSTRUCTIONS

        databases = databases or self.get_databases(split)
        with open(os.path.join(self.directory, "tasks", "tasks_unsampled.json"), "r") as f:
            tasks = [
                AmbigNL2QTask.model_validate(dict(**dic, dataset_instructions=dataset_instructions))
                for dic in json.load(f)
            ]
        tasks = [task for task in tasks if task.db in databases]
        if split == "test":
            tasks = self._upsample_tasks(tasks)
        return tasks

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"arcs+{name}",
                    url=f"sqlite+aiosqlite:///{os.path.join(self.directory, 'databases', 'sqlite', f'{name}.sqlite')}",
                    db_name=name,
                    dbms_semaphore=self._dbms_semaphore,
                    config=self.connector_config.model_copy(update={"max_query_concurrency": self.max_concurrency}),
                )
                for name in databases
            ]
        )

        with open(os.path.join(self.directory, "databases", "column_meanings.json"), "r") as f:
            column_descriptions = {
                key: value.strip().strip("#").strip().replace("\n", " ") for key, value in json.load(f).items()
            }
        for conn in db_connectors:
            for table in conn.schema.tables:
                for column in table.columns:
                    column.description = column_descriptions.get(f"{conn.schema.name}|{table.name}|{column.name}", None)
        return {name: conn for name, conn in zip(databases, db_connectors)}

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset:
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
