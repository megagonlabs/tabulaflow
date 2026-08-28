"""Protocols and registry for research agent strategies."""

from typing import Protocol, ClassVar, TypeAlias, Union
from pydantic import BaseModel
from tabulaflow.research.types import (
    SimpleNL2QTask,
    AmbigNL2QTask,
    DbtTask,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    DbtTaskOutput,
    UserSimulatorProtocol,
)
from tabulaflow.data import SQLConnectorProtocol, DBConnector
from tabulaflow.core.registry import ClassRegistry

__all__ = [
    "AgentConfig",
    "SimpleSQLAgentProtocol",
    "AmbigSQLAgentProtocol",
    "DbtAgentProtocol",
    "NL2QAgent",
    "agent_registry",
]

AgentConfig: TypeAlias = BaseModel


class SimpleSQLAgentProtocol(Protocol):
    """Strategy that predicts one query for a simple task."""

    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[AgentConfig]]

    async def predict_async(self, task: SimpleNL2QTask, db_connector: DBConnector) -> SimpleNL2QTaskOutput: ...


class AmbigSQLAgentProtocol(Protocol):
    """Strategy that resolves and predicts queries for an ambiguous task."""

    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[AgentConfig]]

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: SQLConnectorProtocol, user_simulator: UserSimulatorProtocol
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


class DbtAgentProtocol(Protocol):
    """Strategy that produces a transformed dbt project."""

    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[AgentConfig]]

    async def predict_async(self, task: DbtTask, db_connector: SQLConnectorProtocol) -> DbtTaskOutput: ...


NL2QAgent: TypeAlias = Union[SimpleSQLAgentProtocol, AmbigSQLAgentProtocol, DbtAgentProtocol]


agent_registry = ClassRegistry[NL2QAgent]("agent")
