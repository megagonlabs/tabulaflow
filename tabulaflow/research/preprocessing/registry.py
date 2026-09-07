"""Extension contract and registry for research preprocessing."""

from typing import Any, ClassVar, Literal, Protocol

from tabulaflow.agents.summarization import DBSummarizer
from tabulaflow.agents.trace import Usage
from tabulaflow.core.registry import ClassRegistry
from tabulaflow.data import DataConnector, SQLConnector
from tabulaflow.research.types import NL2QDataset


class ConnectorPreprocessorProtocol(Protocol):
    """Named preprocessing step applied to each SQL database connector."""

    name: ClassVar[str]
    input_type: ClassVar[Literal["db_connector"]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, input_data: SQLConnector) -> object: ...


class DatasetPreprocessorProtocol(Protocol):
    """Named preprocessing step applied once to a complete dataset."""

    name: ClassVar[str]
    input_type: ClassVar[Literal["dataset"]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, input_data: NL2QDataset) -> object: ...


preprocessor_registry = ClassRegistry[Any]("preprocessor")


@preprocessor_registry.register
class DBSummaryPreprocessor(DBSummarizer):
    """Research registry adapter for the reusable database summarizer."""

    name: ClassVar[str] = "db_summarizer"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"

    async def preprocess_async(self, input_data: DataConnector) -> str:
        return await self.summarize(input_data)


__all__ = [
    "ConnectorPreprocessorProtocol",
    "DBSummaryPreprocessor",
    "DatasetPreprocessorProtocol",
    "preprocessor_registry",
]
