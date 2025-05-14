from abc import ABC, abstractmethod
from mintq.schema import BaseNL2QTask
from mintq.db_connector import BaseDBConnector


class BaseNL2QModel(ABC):
    @abstractmethod
    def predict(self, task: BaseNL2QTask, db_connector: BaseDBConnector) -> BaseNL2QTask:
        """
        Predicts the query and returns the trajectory for the given BaseNL2QTask.

        Returns:
            - The updated BaseNL2QTask object with the predicted query.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def llm_name(self) -> str:
        """
        Returns the name of the LLM.
        """
        raise NotImplementedError()
