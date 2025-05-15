from abc import ABC, abstractmethod
from mintq.schema import BaseNL2QTask
from mintq.db_connector import BaseDBConnector


class BaseNL2QModel(ABC):
    name: str

    @abstractmethod
    def predict(self, task: BaseNL2QTask, db_connector: BaseDBConnector) -> BaseNL2QTask:
        """
        Predicts the query and returns the trajectory for the given BaseNL2QTask.

        Returns:
            - The updated BaseNL2QTask object with the predicted query.
        """
        pass

    @abstractmethod
    def get_config(self) -> dict[str, str | int | float | bool]:
        """
        Returns the parameters of the model so that it can be reproduced.

        Returns:
            - A dictionary containing the parameters of the model. Currently we only support literal values.
        """
        pass
