"""Extension contracts and registry for research agent strategies.

A registered strategy declares ``name``, ``task_type``, ``output_type``, and
``config_cls``; provides an async ``from_config_async`` constructor; and implements
the prediction protocol for its task family. Construction stays dynamic because
families accept different optional inputs.
"""

from typing import Any, ClassVar, Protocol

from tabulaflow.core.registry import ClassRegistry
from tabulaflow.data import DBConnector, SQLConnectorProtocol
from tabulaflow.research.types import (
    AmbigNL2QTask,
    DbtTask,
    DbtTaskOutput,
    FlatAmbigNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    UserSimulatorProtocol,
)


class SimpleAgentProtocol(Protocol):
    """Strategy that predicts one query for a simple task."""

    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[Any]

    async def predict_async(self, task: SimpleNL2QTask, db_connector: DBConnector) -> SimpleNL2QTaskOutput: ...


class AmbigSQLAgentProtocol(Protocol):
    """Strategy that resolves and predicts queries for an ambiguous SQL task."""

    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[Any]

    async def predict_async(
        self,
        task: AmbigNL2QTask,
        db_connector: SQLConnectorProtocol,
        user_simulator: UserSimulatorProtocol,
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


class DbtAgentProtocol(Protocol):
    """Strategy that produces a transformed dbt project."""

    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[Any]

    async def predict_async(self, task: DbtTask, db_connector: SQLConnectorProtocol) -> DbtTaskOutput: ...


agent_registry = ClassRegistry[Any]("agent")

__all__ = [
    "AmbigSQLAgentProtocol",
    "DbtAgentProtocol",
    "SimpleAgentProtocol",
    "agent_registry",
]
