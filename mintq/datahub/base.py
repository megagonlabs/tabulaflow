from typing import Protocol, ClassVar, Sequence, Mapping, TypeAlias
from mintq.schema import NL2QDataset, NL2QTask
from mintq.db_connector import NL2QDBConnector
from mintq.registry import Registry


class BaseNL2QDatasetLoader(Protocol):
    """Protocol for NL2Q dataset loaders.

    Implementations provide access to benchmark tasks, database connectors,
    and the evaluation metrics appropriate for the dataset.

    Attributes:
        name: Unique registry key for the dataset (e.g. ``"bird-sql"``).
        splits: Available data splits (e.g. ``["train", "dev"]``).
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
    ) -> Mapping[str, NL2QDBConnector]:
        """Creates database connectors keyed by database name."""
        ...

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset:
        """Loads a complete dataset split (tasks + connectors)."""
        ...


NL2QDatasetLoader: TypeAlias = BaseNL2QDatasetLoader


dataset_registry = Registry[NL2QDatasetLoader]("dataset")
