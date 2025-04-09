from dataclasses import dataclass
from typing import List
import smolagents
from smolagents.memory import MemoryStep, Message, ActionStep
from smolagents.models import MessageRole
from rattq.utils import get_llm_api_cost, parse_query
from rattq.schema import NL2QSample
from rattq.db_connector import BaseDBConnector


class BaseNL2QModel:
    def get_llm_name(self) -> str:
        """
        Returns the name of the LLM.
        """
        raise NotImplementedError()

    def predict(
        self, task: NL2QSample, db_connector: BaseDBConnector
    ) -> tuple[str, list[dict]]:
        """
        Predicts the query and returns the trajectory for the given NL2QSample.

        Returns:
            - query: str
            - trajectory: list[dict]
        """
        raise NotImplementedError()

    def get_metrics(self) -> dict:
        """
        Returns the metrics of the agent.
        """
        raise NotImplementedError()


class SmolagentsNL2QAgent(BaseNL2QModel):
    def __init__(self, smolagent: smolagents.MultiStepAgent):
        self.smolagent = smolagent
        self.feedback_step_indexes = []
        self.input_tokens = 0
        self.output_tokens = 0

    def get_llm_name(self) -> str:
        return self.smolagent.model.model_id

    def format_prompt(self, task: NL2QSample, db_connector: BaseDBConnector) -> str:
        raise NotImplementedError()

    def predict(
        self,
        task: NL2QSample,
        db_connector: BaseDBConnector,
        max_steps: int = 20,
        allow_max_steps_reached: bool = True,
    ) -> tuple[str, list[dict]]:
        prompt = self.format_prompt(task, db_connector)
        query = self.smolagent.run(prompt, reset=True, max_steps=max_steps)
        self._update_token_counts()
        query = parse_query(query)
        query = self._finalize_return(query, allow_max_steps_reached)
        trajectory = self._get_trajectory()
        return query, trajectory

    def _update_token_counts(self):
        token_counts = self.smolagent.monitor.get_total_token_counts()
        self.input_tokens += int(token_counts["input"])
        self.output_tokens += int(token_counts["output"])

    def _finalize_return(self, query: str, allow_max_steps_reached: bool) -> str | None:
        if not allow_max_steps_reached:
            last_step = self.smolagent.memory.steps[-1]
            if isinstance(last_step, ActionStep) and last_step.error:
                return None
        return parse_query(query)

    def _get_trajectory(self) -> list[dict]:
        return {
            "messages": smolagents.models.get_clean_message_list(
                self.smolagent.write_memory_to_messages(),
                flatten_messages_as_text=True,
                role_conversions={
                    "tool-call": "assistant",
                    "tool-response": "user",
                },
            ),
            "tools": [
                smolagents.models.get_tool_json_schema(t)
                for t in list(self.smolagent.tools.values())
            ],
            "parallel_tool_calls": False,
        }

    def get_metrics(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "api_cost_usd": get_llm_api_cost(
                self.smolagent.model.model_id,
                self.input_tokens,
                self.output_tokens,
            ),
        }
