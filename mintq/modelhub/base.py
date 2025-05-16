from typing import Protocol, ClassVar
from mintq.schema import NL2QTask, NL2QTaskOutput
from mintq.db_connector import BaseDBConnector


class BaseNL2QModel(Protocol):
    name: ClassVar[str]

    def predict(self, task: NL2QTask, db_connector: BaseDBConnector) -> NL2QTaskOutput: ...

    def get_config(self) -> dict[str, str | int | float | bool]:
        """Returns the parameter configuration of the model so that it can be reproduced. Currently only for informational purposes."""
        ...
