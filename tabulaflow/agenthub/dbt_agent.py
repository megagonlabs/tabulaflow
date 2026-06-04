"""Dbt agent that uses file_editor and run_dbt tools."""

import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, ClassVar

import jinja2
from pydantic_ai import Agent

from tabulaflow.agenthub.base import agent_registry, BaseAgentConfig
from tabulaflow.agenthub.utils import BasicAgentConfig, get_max_steps_processor, instrument
from tabulaflow.core.db_connector import BaseSQLDBConnector
from tabulaflow.core.formatters import NL2QFormatter, formatter_registry
from tabulaflow.core.preprocessors import DBSummarizer
from tabulaflow.core.types import Usage, Trajectory
from tabulaflow.research.types import DbtTask, DbtTaskOutput
from tabulaflow.toolhub import GetTableSchemaTool, RunQueryTool
from tabulaflow.research.tools import ExecuteBashTool, FileEditorTool, RunDbtTool

logger = logging.getLogger(__name__)


class DbtAgentConfig(BasicAgentConfig):
    db_summarizer_llm: str = "openai-responses:gpt-5.4"
    refresh_schema_on_finish: bool = False
    use_bash_tool: bool = False


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
- You must run `dbt run` to build the project. If it fails, fix the SQL and retry.
- Once the project builds successfully, verify the results and finish.
</goal>

<tool_calling>
Gathering information:
- Use the `file_editor` tool to browse the project directory, read YAML and SQL files, and understand the project structure before making changes.
- Use `get_table_schema` to inspect the schema of source tables in the data warehouse.
- Use `run_query` to run exploratory SQL queries against the source database (e.g. to check row counts, date ranges, or compare overlapping data sources before choosing one).
- Batch multiple `file_editor` view calls in a single step.
{%- if use_bash_tool %}
- You may use `execute_bash` to run shell commands such as `dbt list`, `dbt compile`, or `dbt run`.
- The shell starts in the project directory. Do NOT navigate outside of it.
{%- else %}
- You may use `run_dbt` to list resources or compile SQL without executing.
{%- endif %}

Writing model SQL:
- Read ALL existing SQL model files carefully and follow their patterns exactly in your new models.
- Column names in your output MUST match the YAML schema definitions exactly.
- Use the `file_editor` tool to create new SQL model files or edit existing ones.
{%- if use_bash_tool %}
- Before the first `dbt run`, back up all database files (e.g. `cp *.duckdb *.duckdb.bak`).
  Before each subsequent `dbt run`, restore from the backup (e.g. `cp *.duckdb.bak *.duckdb`) so that every run starts from a clean state.
  A failed `dbt run` can corrupt the database, making it unrecoverable without a backup.
- After writing all required SQL, use `execute_bash` to run `dbt run` to build the project.
{%- else %}
- After writing all required SQL, use `run_dbt` to build the project. You may use the `select` parameter to build specific models.
- Each `dbt run` starts from a fresh copy of the original source database. Any views or tables created by previous runs are automatically rolled back.
  If a run fails, just fix the SQL files and re-run — there is no need to manually clean up database state.
{%- endif %}
- After `dbt run` succeeds, use `get_table_schema` with `refresh=True` to verify the output tables.
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
        self.formatter: NL2QFormatter = formatter_registry.get_class(config.schema_formatter)(
            **config.to_formatter_kwargs()
        )

    @classmethod
    async def from_config_async(cls, config: DbtAgentConfig) -> "DbtAgent":
        return cls(config)

    @instrument
    async def predict_async(self, task: DbtTask, db_connector: BaseSQLDBConnector) -> DbtTaskOutput:
        t0 = time.time()
        assert task.working_dir is not None, "working_dir must be set before calling predict_async"
        working_dir: str = task.working_dir

        db_summarizer = DBSummarizer(llm=self.config.db_summarizer_llm)
        db_summary = await db_summarizer.preprocess_async(db_connector)
        db_document = db_summary.db_summary_markdown

        file_editor = FileEditorTool(working_dir)

        async def _pre_run_hook() -> None:
            await db_connector.disconnect_async()
            # Restore DuckDB files from pristine backup before each dbt run
            # to prevent unrecoverable corruption caused by previous dbt runs.
            db_files = list(Path(working_dir).resolve().glob("*.duckdb"))
            for db_file in db_files:
                backup = db_file.with_suffix(".duckdb.pristine")
                if not backup.exists():
                    shutil.copy2(db_file, backup)
                shutil.copy2(backup, db_file)

        get_table_schema = GetTableSchemaTool(
            db_connector,
            self.formatter,  # type: ignore[arg-type]
            compress=self.config.compress_schema,
            add_description=self.config.use_column_description,
            disconnect_on_finish=True,
            enable_refresh=True,
        )
        run_query = RunQueryTool(
            db_connector,
            timeout=30,
            max_visible_rows=20,
            disconnect_on_finish=True,
        )

        if self.config.use_bash_tool:
            dbt_path = shutil.which("dbt") or str(Path(sys.prefix) / "bin" / "dbt")
            if not os.path.isfile(dbt_path):
                raise RuntimeError(
                    "dbt not found on PATH or in the current Python environment. "
                    "Install dbt or activate the correct virtualenv."
                )
            dbt_bin_dir = str(Path(dbt_path).parent)
            run_tool: ExecuteBashTool | RunDbtTool = ExecuteBashTool(
                working_dir=working_dir,
                init_commands=[f'export PATH="{dbt_bin_dir}:$PATH"'],
            )
        else:
            run_tool = RunDbtTool(working_dir, pre_run_hook=_pre_run_hook)

        system_prompt = jinja2.Template(DBT_AGENT_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
            db_document=db_document,
            use_bash_tool=self.config.use_bash_tool,
        )

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[
                file_editor.as_pydantic_ai_tool(),
                run_query.as_pydantic_ai_tool(),
                run_tool.as_pydantic_ai_tool(),
                get_table_schema.as_pydantic_ai_tool(),
            ],
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )

        await db_connector.disconnect_async()

        result = await agent.run(
            f"Complete the dbt project by writing the missing SQL model files and running `dbt run` successfully:\n{task.question}"
        )
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DBT-AGENT")

        pred_db_path = _find_duckdb_file(task.working_dir)

        if self.config.refresh_schema_on_finish:
            await db_connector.refresh_schema_async()
        pred_db_schema = db_connector.schema

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
            run_tool.name: run_tool.metrics().model_dump(),
            "get_table_schema": get_table_schema.metrics().model_dump(),
            "run_query": run_query.metrics().model_dump(),
        }

        dbt_run_success = run_tool.metrics().last_run_success if isinstance(run_tool, RunDbtTool) else None

        return DbtTaskOutput(
            **task.model_dump(),
            pred_db_path=pred_db_path,
            pred_db_schema=pred_db_schema,
            pred_model_files=pred_model_files,
            dbt_run_success=dbt_run_success,
            trajectory=trajectory,
            usage=usage,
            inference_metrics=metrics,
        )
