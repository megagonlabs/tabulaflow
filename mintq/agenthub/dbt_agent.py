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

You are working on a dbt project that uses DuckDB as the data warehouse.
Your task is to complete the project by writing the missing SQL model files
so that `dbt run` succeeds and produces the correct tables.

<goal>
- Read the dbt project files (dbt_project.yml, profiles.yml, schema YAML
  files) to understand the project structure and what models need to be built.
- Identify which SQL model files are missing or incomplete by examining the
  YAML schema definitions and the existing model files.
- Write the missing SQL model files using the `file_editor` tool.
- Run `dbt run` using the `run_dbt` tool to build the project.
- If `dbt run` fails, read the error output, fix the SQL, and retry.
- You may use `run_dbt(command="ls")` to list all resources in the project.
- You may use `run_dbt(command="compile")` to check SQL compilation without
  executing.
- You may use the `run_dbt` tool with `select` to run specific models.
- Do NOT modify YAML files. Only create or edit SQL files.
- Once the project builds successfully, verify the results and finish.
</goal>

<tool_calling>
Gathering information:
- Use the `file_editor` tool to browse the project directory, read YAML and SQL files, and understand the project structure before making changes.
- You may use `run_dbt` with `command="ls"` to list all resources or `command="compile"` to check SQL compilation without executing.

Writing model SQL:
- Use the `file_editor` tool to create new SQL model files or edit existing ones.
- After writing all required SQL, use `run_dbt` with `command="run"` to build the project. You may use the `select` parameter to build specific models.
- If `dbt run` fails, read the error output, fix the SQL, and retry.
- Be THOROUGH. Make sure all models defined in the YAML files are implemented before finishing.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{ dataset_instructions }}
</dataset_instructions>
{%- endif %}
""".strip()


class DbtFinishTool:
    """Finish tool for dbt agent that verifies dbt run was called."""

    name: ClassVar = "finish"

    def __init__(self) -> None:
        self._metrics = _DbtFinishMetrics()

    def as_pydantic_ai_tool(self) -> ToolOutput[None]:
        def finish(ctx: RunContext) -> None:
            """Finish the task. Only call this after `dbt run` succeeds.

            Example:
            ```python
            finish()
            ```
            """
            trajectory = Trajectory.from_pydantic_ai_messages(ctx.messages)
            for msg in trajectory.messages[::-1]:
                if msg.role == "assistant":
                    for tc in msg.tool_calls[::-1]:
                        if tc.name == "run_dbt" and tc.arguments is not None:
                            self._metrics.num_calls += 1
                            return None
            self._metrics.error_no_dbt_run += 1
            raise ModelRetry(
                "You must run `run_dbt` at least once before finishing."
            )

        return ToolOutput(finish, name="finish")

    def metrics(self) -> "_DbtFinishMetrics":
        return self._metrics


class _DbtFinishMetrics(BaseModel):
    num_calls: int = 0
    error_no_dbt_run: int = 0


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
    async def predict_async(
        self, task: DbtTask, db_connector: BaseSQLDBConnector
    ) -> DbtTaskOutput:
        t0 = time.time()
        assert task.working_dir is not None, "working_dir must be set before calling predict_async"

        file_editor = FileEditorTool(task.working_dir)
        run_dbt = RunDbtTool(task.working_dir)
        finish = DbtFinishTool()

        system_prompt = jinja2.Template(DBT_AGENT_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
        )

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[
                file_editor.as_pydantic_ai_tool(),
                run_dbt.as_pydantic_ai_tool(),
            ],
            output_type=finish.as_pydantic_ai_tool(),
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )

        result = await agent.run(task.question)
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(
            result.all_messages(), id="TRJY-DBT-AGENT"
        )

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
        metrics["steps"] = sum(
            1 for msg in trajectory.messages if msg.role == "assistant"
        )
        metrics["retry_prompt"] = sum(
            1 for msg in trajectory.messages
            if msg.role == "tool" and msg.is_retry_prompt
        )
        metrics["tools"] = {
            "file_editor": file_editor.metrics().model_dump(),
            "run_dbt": run_dbt.metrics().model_dump(),
            "finish": finish.metrics().model_dump(),
        }

        return DbtTaskOutput(
            **task.model_dump(),
            pred_db_path=pred_db_path,
            pred_model_files=pred_model_files,
            trajectory=trajectory,
            usage=usage,
            inference_metrics=metrics,
        )
