"""Extension contract and registry for research preprocessing."""

from typing import Any, ClassVar, Literal, Protocol

from tabulaflow.agents.summarization import DBSummarizer
from tabulaflow.agents.trace import Usage
from tabulaflow.core.registry import ClassRegistry
from tabulaflow.data.protocols import DBConnector


class PreprocessorProtocol(Protocol):
    """Named preprocessing step with usage accounting."""

    name: ClassVar[str]
    input_type: ClassVar[Literal["db_connector", "dataset"]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, input_data: Any) -> object: ...


preprocessor_registry = ClassRegistry[Any]("preprocessor")


@preprocessor_registry.register
class DBSummaryPreprocessor(DBSummarizer):
    """Research registry adapter for the reusable database summarizer."""

    name: ClassVar[str] = "db_summarizer"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"

    async def preprocess_async(self, input_data: DBConnector) -> str:
        return await self.summarize(input_data)


__all__ = ["DBSummaryPreprocessor", "PreprocessorProtocol", "preprocessor_registry"]
