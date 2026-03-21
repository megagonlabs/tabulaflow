"""Dbt agent that uses file_editor and run_dbt tools."""

import logging
import os
import time
from typing import Any, ClassVar

import jinja2
from pydantic_ai import Agent

from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import BasicAgentConfig, get_max_steps_processor, instrument
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter, formatter_registry
from mintq.preprocessors import DBSummarizer
from mintq.schema import DbtTask, DbtTaskOutput, Usage, Trajectory
from mintq.toolhub import FileEditorTool, GetTableSchemaTool, RunDbtTool

logger = logging.getLogger(__name__)


class DbtAgentConfig(BasicAgentConfig):
    db_summarizer_llm: str = "openai-responses:gpt-5.4"


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
- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information and follow the most natural interpretation.
- Ensure the models accurately reflect the original question without adding or omitting any transformations or conditions.
- Read the dbt project files to understand the project structure, the data warehouse adapter, and what models need to be built.
- Identify which SQL model files are missing or incomplete by examining the YAML schema definitions and the existing model files.
- Write the missing SQL model files. Do NOT modify YAML files.
- You must run `dbt run` to build the project. If it fails, read the error output, fix the SQL, and retry.
- Once the project builds successfully, verify the results and finish.
</goal>

<tool_calling>
Gathering information:
- Use the `file_editor` tool to browse the project directory, read YAML and SQL files, and understand the project structure before making changes.
- Use `get_table_schema` to inspect the schema of source tables in the data warehouse.
- Batch multiple `file_editor` view calls in a single step.
- You may use `run_dbt` to list resources or compile SQL without executing.

Writing model SQL:
- Use the `file_editor` tool to create new SQL model files or edit existing ones.
- After writing all required SQL, use `run_dbt` to build the project. You may use the `select` parameter to build specific models.
- If `dbt run` fails, read the error output, fix the SQL, and retry.
- After `dbt run` succeeds, use `get_table_schema` to verify that the output tables.
- Be THOROUGH. Make sure all models defined in the YAML files are implemented before finishing.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{ dataset_instructions }}
</dataset_instructions>
{%- endif %}
{%- if db_document %}

<db_document>
{{ db_document }}
</db_document>
{%- endif %}
""".strip()


@agent_registry.register
class DbtAgent:
    name: ClassVar = "dbt_agent"
    task_type: ClassVar = "dbt"
    output_type: ClassVar = "dbt"
    config_cls: ClassVar[type[BaseAgentConfig]] = DbtAgentConfig

    def __init__(self, config: DbtAgentConfig):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)(
            **config.to_formatter_kwargs()
        )

    @classmethod
    async def from_config_async(cls, config: DbtAgentConfig) -> "DbtAgent":
        return cls(config)

    @instrument
    async def predict_async(self, task: DbtTask, db_connector: BaseSQLDBConnector) -> DbtTaskOutput:
        t0 = time.time()
        assert task.working_dir is not None, "working_dir must be set before calling predict_async"

        db_summarizer = DBSummarizer(llm=self.config.db_summarizer_llm)
        db_summary = await db_summarizer.preprocess_async(db_connector)
        db_document = db_summary.db_summary_markdown

        file_editor = FileEditorTool(task.working_dir)
        run_dbt = RunDbtTool(task.working_dir, pre_run_hook=getattr(db_connector, "dispose_engine_async", None))
        get_table_schema = GetTableSchemaTool(
            db_connector,
            self.formatter,
            compress=self.config.compress_schema,
            add_description=self.config.use_column_description,
        )

        system_prompt = jinja2.Template(DBT_AGENT_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
            db_document=db_document,
        )

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[
                file_editor.as_pydantic_ai_tool(),
                run_dbt.as_pydantic_ai_tool(),
                get_table_schema.as_pydantic_ai_tool(),
            ],
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )

        result = await agent.run(
            f"Complete the dbt project by writing the missing SQL model files and running `dbt run` successfully:\n{task.question}"
        )
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
            "get_table_schema": get_table_schema.metrics().model_dump(),
        }

        dbt_run_success = run_dbt.metrics().last_run_success

        return DbtTaskOutput(
            **task.model_dump(),
            pred_db_path=pred_db_path,
            pred_model_files=pred_model_files,
            dbt_run_success=dbt_run_success,
            trajectory=trajectory,
            usage=usage,
            inference_metrics=metrics,
        )
