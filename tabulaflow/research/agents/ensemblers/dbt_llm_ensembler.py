"""LLM-based ensembler for DBT tasks (multi-choice only).

Presents candidate model files, build status, and output table schemas
to an LLM and asks it to select the best candidate.
"""

import logging
from typing import Any, ClassVar

import jinja2
from pydantic import BaseModel
from pydantic_ai import ToolOutput

from tabulaflow.research.agents.registry import AgentConfig
from tabulaflow.research.agents.utils import instrument
from tabulaflow.data import SQLConnectorProtocol
from tabulaflow.output.formatting import SQLDDLSchemaFormatter
from tabulaflow.agents.summarization import DBSummarizer
from tabulaflow.agents.llm import make_model_settings
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.types import DbtTask, DbtTaskOutput
from tabulaflow.agents.llm import make_agent

logger = logging.getLogger(__name__)

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
""".strip()

DBT_CANDIDATE_TEMPLATE = """
<candidate number="{{ number }}">
<model_files>
{%- for path, content in model_files.items() %}
<file path="{{ path }}">
{{ content }}
</file>
{%- endfor %}
</model_files>
{%- if output_schema %}
<output_schema>
{{ output_schema }}
</output_schema>
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


class DbtLLMEnsemblerConfig(BaseModel):
    result_dirs: list[str]
    llm: str = "openai-responses:gpt-5-mini"
    db_summarizer_llm: str = "openai-responses:gpt-5.4"
    skip_failed_runs: bool = True
    deduplicate_results: bool = True
    temperature: float | None = None
    reasoning_effort: str | None = None
    service_tier: str | None = None

    def to_model_settings(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if self.temperature is not None:
            res["temperature"] = self.temperature
        res.update(
            make_model_settings(
                model=self.llm,
                reasoning_effort=self.reasoning_effort,
                service_tier=self.service_tier,
            )
        )
        return res


class DbtLLMEnsembler:
    name: ClassVar = "dbt_llm_ensembler"
    task_type: ClassVar = "dbt"
    output_type: ClassVar = "dbt"
    config_cls: ClassVar[type[AgentConfig]] = DbtLLMEnsemblerConfig

    def __init__(self, config: DbtLLMEnsemblerConfig):
        self.config = config
        self.formatter = SQLDDLSchemaFormatter()

    @classmethod
    async def from_config_async(cls, config: DbtLLMEnsemblerConfig) -> "DbtLLMEnsembler":
        return cls(config)

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
        db_connector: SQLConnectorProtocol,
        task_outputs: list[DbtTaskOutput],
    ) -> DbtTaskOutput:
        candidates = list(task_outputs)

        if not candidates:
            return task_outputs[0]

        # Filter out candidates where dbt run failed
        if self.config.skip_failed_runs:
            candidates = [o for o in candidates if o.dbt_run_success is not False]

        # Filter out candidates with no model files
        candidates = [o for o in candidates if o.pred_model_files]

        if self.config.deduplicate_results:
            candidates = self._deduplicate_candidates(candidates)

        if len(candidates) <= 1:
            best = candidates[0] if candidates else task_outputs[0]
            return DbtTaskOutput(
                **task.model_dump(),
                pred_db_path=best.pred_db_path,
                pred_db_schema=best.pred_db_schema,
                pred_model_files=best.pred_model_files,
                dbt_run_success=best.dbt_run_success,
                dbt_run_log=best.dbt_run_log,
            )

        # Get db summary for context
        db_summarizer = DBSummarizer(llm=self.config.db_summarizer_llm)
        db_summary = await db_summarizer.summarize(db_connector)

        # Build candidate descriptions
        candidate_strs: list[str] = []
        for i, output in enumerate(candidates):
            output_schema = self.formatter.format(output.pred_db_schema) if output.pred_db_schema else ""
            candidate_str = jinja2.Template(DBT_CANDIDATE_TEMPLATE).render(
                number=i + 1,
                model_files=output.pred_model_files,
                output_schema=output_schema,
            )
            candidate_strs.append(candidate_str)

        system_prompt = jinja2.Template(DBT_LLM_ENSEMBLE_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
            db_document=db_summary,
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

        agent = make_agent(
            self.config.llm,
            instructions=system_prompt,
            output_type=ToolOutput(answer, name="answer"),
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(user_prompt)
        usage = Usage.from_pydantic_ai_usage(result.usage, self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DBT-ENSEMBLE")

        best_output = candidates[result.output]

        return DbtTaskOutput(
            **task.model_dump(),
            pred_db_path=best_output.pred_db_path,
            pred_db_schema=best_output.pred_db_schema,
            pred_model_files=best_output.pred_model_files,
            dbt_run_success=best_output.dbt_run_success,
            dbt_run_log=best_output.dbt_run_log,
            usage=usage,
            trajectory=trajectory,
        )
