"""Extension contract, selection helpers, and registry for benchmark loaders."""

import random
from typing import ClassVar, Mapping, Protocol, Sequence, TypeVar

from tabulaflow.research.types import NL2QDataset, NL2QTask
from tabulaflow.data import DBConnector
from tabulaflow.core.registry import ClassRegistry

TaskT = TypeVar("TaskT", bound=NL2QTask)


def select_tasks(
    tasks: list[TaskT],
    qids: list[str] | None = None,
    subsample_size: int | None = None,
) -> list[TaskT]:
    """Filter by QID, then take a deterministic random sample."""
    if qids is not None:
        requested = set(qids)
        available = {task.qid for task in tasks}
        missing = requested - available
        if missing:
            raise ValueError(f"Unknown QIDs: {sorted(missing)}")
        tasks = [task for task in tasks if task.qid in requested]

    if subsample_size is None:
        return tasks
    if subsample_size < 1:
        raise ValueError("subsample_size must be at least 1")
    if subsample_size > len(tasks):
        raise ValueError(f"Cannot sample {subsample_size} tasks from {len(tasks)} available tasks")
    if subsample_size == len(tasks):
        return tasks
    return random.Random(42).sample(tasks, subsample_size)


def selected_databases(tasks: Sequence[NL2QTask]) -> list[str]:
    """Return task database names in first-seen order."""
    return list(dict.fromkeys(task.db for task in tasks))


class DatasetLoaderProtocol(Protocol):
    """Loader for one registered NL2Q benchmark.

    Implementations provide access to benchmark tasks, database connectors,
    and the evaluation metrics appropriate for the dataset.

    Attributes:
        name: Unique registry key for the dataset (e.g. ``"bird-sql"``).
        splits: Non-empty available data splits, with the default first.
        default_metrics: Metric names evaluated by default for this dataset.
            Can be overridden via ``--metrics`` on the evaluate CLI.
    """

    name: ClassVar[str]
    splits: ClassVar[list[str]]
    default_metrics: ClassVar[list[str]]

    def get_databases(self, split: str) -> list[str]:
        """Returns the list of database names available in the given split."""
        ...

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> Sequence[NL2QTask]:
        """Loads tasks for a split, optionally filtered to specific databases."""
        ...

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> Mapping[str, DBConnector]:
        """Creates database connectors keyed by database name."""
        ...

    async def get_split_async(
        self,
        split: str,
        databases: list[str] | None = None,
        subsample_size: int | None = None,
        qids: list[str] | None = None,
    ) -> NL2QDataset:
        """Load selected tasks and the connectors they require.

        QID filtering precedes deterministic sampling. Unknown QIDs and invalid
        sample sizes raise ``ValueError``.
        """
        ...


dataset_registry = ClassRegistry[DatasetLoaderProtocol]("dataset")

__all__ = ["DatasetLoaderProtocol", "dataset_registry", "select_tasks", "selected_databases"]
