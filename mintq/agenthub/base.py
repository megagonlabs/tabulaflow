from typing import Protocol, ClassVar, Any, Type
from mintq.schema import NL2QTask, NL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class BaseAgentConfig(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


class BaseAsyncNL2QAgent(Protocol):
    name: ClassVar[str]
    config_cls: ClassVar[Type[BaseAgentConfig]]

    async def from_config_async(self, config: BaseAgentConfig) -> "BaseAsyncNL2QAgent": ...

    async def predict_async(self, task: NL2QTask, db_connector: BaseAsyncDBConnector) -> NL2QTaskOutput: ...
