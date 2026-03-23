"""LLM-based ensembler for DBT tasks (multi-choice only).

Presents candidate model files, build status, and output table previews
to an LLM and asks it to select the best candidate.
"""

import logging
import os
from typing import Any, ClassVar

import duckdb
import jinja2
import pandas as pd
from pydantic import BaseModel
from pydantic_ai import Agent, ToolOutput

from mintq.agenthub.base import BaseAgentConfig
from mintq.agenthub.utils import instrument
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.utils import format_df
from mintq.preprocessors import DBSummarizer
from mintq.schema import DbtTask, DbtTaskOutput, Usage, Trajectory

logger = logging.getLogger(__name__)

_TABLE_PREVIEW_MAX_ROWS = 10

DBT_LLM_ENSEMBLE_SYSTEM_PROMPT = """
You are a helpful AI data engineering expert proficient in dbt (data build tool) and SQL.
You are given a natural-language instruction describing a data transformation to build, and multiple candidate dbt model implementations along with their build results.
Your task is to select the **single best** candidate whose SQL model files most accurately implement the required transformation.
The correct implementation should faithfully reflect the instruction and dataset requirements without adding or omitting transformations.

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

DBT_CANDIDATE_TEMPLATE = """
<candidate number="{{ number }}">
<dbt_run_success>{{ dbt_run_success }}</dbt_run_success>
<model_files>
{%- for path, content in model_files.items() %}
<file path="{{ path }}">
{{ content }}
</file>
{%- endfor %}
</model_files>
{%- if table_previews %}
<output_tables>
{%- for table_name, preview in table_previews.items() %}
<table name="{{ table_name }}">
{{ preview }}
</table>
{%- endfor %}
</output_tables>
{%- endif %}
</candidate>
""".strip()

DBT_USER_PROMPT_TEMPLATE = """
Instruction: {{ question }}
{%- if question_instructions %}
{{ question_instructions }}
{%- endif %}

Here are the candidate dbt implementations and their results:

{% for candidate in candidates %}
{{ candidate }}
{% endfor %}

Select the number of the best candidate.
""".strip()


def _read_duckdb_table_safe(db_path: str, table_name: str) -> pd.DataFrame | None:
    """Read a table from a DuckDB file, returning None on any failure."""
    try:
        con = duckdb.connect(database=db_path, read_only=True)
        try:
            return con.execute(f"SELECT * FROM {table_name}").fetchdf()
        finally:
            con.close()
    except Exception:
        return None


def _format_table_preview(df: pd.DataFrame) -> str:
    if df.empty:
        return "(empty table)"
    preview = format_df(df, max_visible_rows=_TABLE_PREVIEW_MAX_ROWS)
    preview += f"\n({len(df)} rows)"
    return preview


class DbtLLMEnsemblerConfig(BaseModel):
    result_dirs: list[str]
    llm: str = "openai-responses:gpt-5-mini"
    db_summarizer_llm: str = "openai-responses:gpt-5.4"
    skip_failed_runs: bool = True
    deduplicate_results: bool = True
    temperature: float | None = None
    openai_reasoning_effort: str | None = None
    openai_service_tier: str | None = None

    def to_model_settings(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if self.temperature is not None:
            res["temperature"] = self.temperature
        if self.openai_reasoning_effort is not None:
            res["openai_reasoning_effort"] = self.openai_reasoning_effort
            res["openai_reasoning_summary"] = "detailed"
        if self.openai_service_tier is not None:
            res["openai_service_tier"] = self.openai_service_tier
        return res


class DbtLLMEnsembler:
    name: ClassVar = "dbt_llm_ensembler"
    task_type: ClassVar = "dbt"
    output_type: ClassVar = "dbt"
    config_cls: ClassVar[type[BaseAgentConfig]] = DbtLLMEnsemblerConfig

    def __init__(self, config: DbtLLMEnsemblerConfig):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: DbtLLMEnsemblerConfig) -> "DbtLLMEnsembler":
        return cls(config)

    def _get_table_previews(self, output: DbtTaskOutput, task: DbtTask) -> dict[str, str]:
        """Read gold tables from the candidate's DuckDB and return formatted previews."""
        previews: dict[str, str] = {}
        if not output.pred_db_path or not os.path.exists(output.pred_db_path):
            return previews
        for gt in task.gold_tables:
            df = _read_duckdb_table_safe(output.pred_db_path, gt.table_name)
            if df is not None:
                previews[gt.table_name] = _format_table_preview(df)
        return previews

    def _deduplicate_candidates(self, candidates: list[DbtTaskOutput]) -> list[DbtTaskOutput]:
        """Deduplicate candidates with identical model file contents."""
        seen: set[tuple[tuple[str, str], ...]] = set()
        deduped: list[DbtTaskOutput] = []
        for output in candidates:
            hashable = tuple(sorted(output.pred_model_files.items()))
            if hashable not in seen:
                seen.add(hashable)
                deduped.append(output)
        return deduped

    @instrument
    async def ensemble_async(
        self,
        task: DbtTask,
        db_connector: BaseSQLDBConnector,
        task_outputs: list[DbtTaskOutput],
    ) -> DbtTaskOutput:
        candidates = list(task_outputs)

        if not candidates:
            return task_outputs[0]

        # Filter out candidates where dbt run failed
        if self.config.skip_failed_runs:
            candidates = [o for o in candidates if o.dbt_run_success is True]

        # Filter out candidates with no model files
        candidates = [o for o in candidates if o.pred_model_files]

        if self.config.deduplicate_results:
            candidates = self._deduplicate_candidates(candidates)

        if len(candidates) <= 1:
            best = candidates[0] if candidates else task_outputs[0]
            return DbtTaskOutput(
                **task.model_dump(),
                pred_db_path=best.pred_db_path,
                pred_model_files=best.pred_model_files,
                dbt_run_success=best.dbt_run_success,
                dbt_run_log=best.dbt_run_log,
            )

        # Get db summary for context
        db_summarizer = DBSummarizer(llm=self.config.db_summarizer_llm)
        db_summary = await db_summarizer.preprocess_async(db_connector)

        # Build candidate descriptions
        candidate_strs: list[str] = []
        for i, output in enumerate(candidates):
            table_previews = self._get_table_previews(output, task)
            candidate_str = jinja2.Template(DBT_CANDIDATE_TEMPLATE).render(
                number=i + 1,
                dbt_run_success=output.dbt_run_success,
                model_files=output.pred_model_files,
                table_previews=table_previews,
            )
            candidate_strs.append(candidate_str)

        system_prompt = jinja2.Template(DBT_LLM_ENSEMBLE_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
            db_document=db_summary.db_summary_markdown,
        )

        user_prompt = jinja2.Template(DBT_USER_PROMPT_TEMPLATE).render(
            question=task.question,
            question_instructions=task.question_instructions,
            candidates=candidate_strs,
        )

        num_candidates = len(candidates)

        def answer(number: int) -> int:
            """Select the best candidate.

            Args:
                number: The number of the best candidate.
            """
            if number < 1 or number > num_candidates:
                logger.warning(
                    f"LLM returned out-of-range number {number} for {num_candidates} candidates; falling back to 1."
                )
                return 0
            return number - 1

        agent = Agent[None, int](  # type: ignore
            model=self.config.llm,
            instructions=system_prompt,
            output_type=ToolOutput(answer, name="answer"),
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(user_prompt)
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DBT-ENSEMBLE")

        best_output = candidates[result.output]

        return DbtTaskOutput(
            **task.model_dump(),
            pred_db_path=best_output.pred_db_path,
            pred_model_files=best_output.pred_model_files,
            dbt_run_success=best_output.dbt_run_success,
            dbt_run_log=best_output.dbt_run_log,
            usage=usage,
            trajectory=trajectory,
        )
