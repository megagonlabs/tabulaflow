from dataclasses import dataclass
from typing import List
import smolagents
from smolagents.memory import MemoryStep, Message, ActionStep
from smolagents.models import MessageRole
from rattq.utils import get_llm_api_cost, parse_query


@dataclass
class FeedbackStep(MemoryStep):
    feedback: str

    def to_messages(self, summary_mode: bool, **kwargs) -> List[Message]:
        if summary_mode:
            return []
        return [
            Message(
                role=MessageRole.USER,
                content=[{"type": "text", "text": self.feedback.strip()}],
            )
        ]


class NL2QAgent:
    def __init__(self, smolagent: smolagents.MultiStepAgent):
        self.smolagent = smolagent
        self.feedback_step_indexes = []
        self.input_tokens = 0
        self.output_tokens = 0

    def get_llm_name(self) -> str:
        return self.smolagent.model.model_id

    def remove_last_k_actions(self, num: int):
        for _ in range(num):
            self.smolagent.memory.steps.pop(-1)

    def truncate_to_first_k_actions(self, num: int):
        self.smolagent.memory.steps = self.smolagent.memory.steps[:num + 1]

    def add_feedback(self, feedback: str):
        self.feedback_step_indexes.append(len(self.smolagent.memory.steps))
        self.smolagent.memory.steps.append(FeedbackStep(feedback=feedback))

    def remove_all_feedback(self):
        for idx in self.feedback_step_indexes[::-1]:
            self.smolagent.memory.steps.pop(idx)
        self.feedback_step_indexes = []

    def run_new_task(
        self, task: str, max_steps: int, allow_max_steps_reached: bool = True
    ) -> str | None:
        query = self.smolagent.run(task, reset=True, max_steps=max_steps)
        query = parse_query(query)
        self._update_token_counts()
        return self._finalize_return(query, allow_max_steps_reached)

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

    def continue_task(
        self, max_steps: int, allow_max_steps_reached: bool = False
    ) -> str | None:
        query = list(self.smolagent._run(task=None, max_steps=max_steps))[-1]
        self._update_token_counts()
        return self._finalize_return(query, allow_max_steps_reached)

    def get_trajectory(self) -> list[dict]:
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
