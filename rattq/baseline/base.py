from abc import ABC, abstractmethod
import time
import smolagents
from smolagents.memory import ActionStep
from rattq.utils import get_llm_api_cost, parse_query
from rattq.schema import NL2QTask
from rattq.db_connector import BaseDBConnector


class BaseNL2QModel(ABC):
    @abstractmethod
    def predict(
        self, task: NL2QTask, db_connector: BaseDBConnector
    ) -> tuple[str, list[dict], dict]:
        """
        Predicts the query and returns the trajectory for the given NL2QTask.

        Returns:
            - query: str
            - trajectory: list[dict]
            - metrics: dict
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def llm_name(self) -> str:
        """
        Returns the name of the LLM.
        """
        raise NotImplementedError()


class SmolagentsNL2QAgent(BaseNL2QModel):
    @property
    def llm_name(self) -> str:
        return self.smolagent.model.model_id

    @abstractmethod
    def format_prompt(self, task: NL2QTask, db_connector: BaseDBConnector) -> str:
        pass

    @abstractmethod
    def get_smolagent(
        self, task: NL2QTask, db_connector: BaseDBConnector
    ) -> smolagents.MultiStepAgent:
        pass

    def predict(
        self,
        task: NL2QTask,
        db_connector: BaseDBConnector,
        max_steps: int = 20,
        allow_max_steps_reached: bool = True,
    ) -> tuple[str, list[dict]]:
        t0 = time.time()
        agent = self.get_smolagent(task, db_connector)
        prompt = self.format_prompt(task, db_connector)
        query = agent.run(prompt, reset=True, max_steps=max_steps)

        query = parse_query(query)
        if not allow_max_steps_reached:
            last_step = agent.memory.steps[-1]
            if isinstance(last_step, ActionStep) and last_step.error:
                query = None

        # Re-construct trajectory
        trajectory = {
            "messages": smolagents.models.get_clean_message_list(
                agent.write_memory_to_messages(),
                flatten_messages_as_text=True,
                role_conversions={
                    "tool-call": "assistant",
                    "tool-response": "user",
                },
            ),
            "tools": [
                smolagents.models.get_tool_json_schema(t)
                for t in list(agent.tools.values())
            ],
            "parallel_tool_calls": False,
        }

        # Compute metrics
        token_counts = agent.monitor.get_total_token_counts()
        input_tokens = int(token_counts["input"])
        output_tokens = int(token_counts["output"])
        metrics = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "api_cost_usd": get_llm_api_cost(
                agent.model.model_id,
                input_tokens,
                output_tokens,
            ),
            "latency": round(time.time() - t0, 1),
            "trajectory_steps": sum(
                1
                for msg in trajectory["messages"]
                if msg["role"].lower() == "assistant"
            ),
        }
        return query, trajectory, metrics
