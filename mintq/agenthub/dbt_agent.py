"""Dbt agent that uses file_editor and run_dbt tools."""

import logging
import os
import time
from typing import Any, ClassVar

import jinja2
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ModelRetry, ToolOutput

from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import BasicAgentConfig, get_max_steps_processor, instrument
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import DbtTask, DbtTaskOutput, Usage, Trajectory
from mintq.toolhub import FileEditorTool, RunDbtTool

logger = logging.getLogger(__name__)


def _find_duckdb_file(directory: str) -> str | None:
    """Return the path of the first ``.duckdb`` file in *directory*, or ``None``."""
    for f in os.listdir(directory):
        if f.endswith(".duckdb"):
            return os.path.join(directory, f)
    return None


DBT_AGENT_SYSTEM_PROMPT = """
You are a data engineer proficient in dbt (data build tool) and SQL.

You are working on an incomplete dbt project. Your task is to complete the project by writing the missing SQL model files so that `dbt run` succeeds and produces the correct tables.

You are an agent - please keep going until the project builds successfully, before finishing. Only finish your turn when you are sure that the problem is solved. Autonomously resolve the task to the best of your ability.

<goal>
- Read the dbt project files to understand the project structure, the data warehouse adapter, and what models need to be built.
- Identify which SQL model files are missing or incomplete by examining the YAML schema definitions and the existing model files.
- Write the missing SQL model files. Do NOT modify YAML files.
- Run `dbt run` to build the project. If it fails, read the error output, fix the SQL, and retry.
- Once the project builds successfully, verify the results and finish.
</goal>

<tool_calling>
Gathering information:
- Use the `file_editor` tool to browse the project directory, read YAML and SQL files, and understand the project structure before making changes.
- You may use `run_dbt` to list resources or compile SQL without executing.

Writing model SQL:
- Use the `file_editor` tool to create new SQL model files or edit existing ones.
- After writing all required SQL, use `run_dbt` to build the project. You may use the `select` parameter to build specific models.
- If `dbt run` fails, read the error output, fix the SQL, and retry.
- Be THOROUGH. Make sure all models defined in the YAML files are implemented before finishing.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{ dataset_instructions }}
</dataset_instructions>
{%- endif %}
""".strip()


@agent_registry.register
class DbtAgent:
    name: ClassVar = "dbt_agent"
    task_type: ClassVar = "dbt"
    output_type: ClassVar = "dbt"
    config_cls: ClassVar[type[BaseAgentConfig]] = BasicAgentConfig

    def __init__(self, config: BasicAgentConfig):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "DbtAgent":
        return cls(config)

    @instrument
    async def predict_async(self, task: DbtTask, db_connector: BaseSQLDBConnector) -> DbtTaskOutput:
        t0 = time.time()
        assert task.working_dir is not None, "working_dir must be set before calling predict_async"

        file_editor = FileEditorTool(task.working_dir)
        run_dbt = RunDbtTool(task.working_dir)

        system_prompt = jinja2.Template(DBT_AGENT_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
        )

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[
                file_editor.as_pydantic_ai_tool(),
                run_dbt.as_pydantic_ai_tool(),
            ],
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )

        result = await agent.run(task.question)
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DBT-AGENT")

        pred_db_path = _find_duckdb_file(task.working_dir)

        pred_model_files: dict[str, str] = {}
        models_dir = os.path.join(task.working_dir, "models")
        if os.path.isdir(models_dir):
            for root, _dirs, files in os.walk(models_dir):
                for f in files:
                    if f.endswith(".sql"):
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, task.working_dir)
                        try:
                            pred_model_files[rel] = open(full).read()
                        except OSError:
                            pass

        metrics: dict[str, Any] = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {
            "file_editor": file_editor.metrics().model_dump(),
            "run_dbt": run_dbt.metrics().model_dump(),
        }

        return DbtTaskOutput(
            **task.model_dump(),
            pred_db_path=pred_db_path,
            pred_model_files=pred_model_files,
            trajectory=trajectory,
            usage=usage,
            inference_metrics=metrics,
        )
