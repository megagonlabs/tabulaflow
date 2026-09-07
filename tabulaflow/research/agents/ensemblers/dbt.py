"""LLM-based ensembler for DBT tasks (multi-choice only).

Presents candidate model files, build status, and output table schemas
to an LLM and asks it to select the best candidate.
"""

from typing import Any, ClassVar

import jinja2
from pydantic import BaseModel
from pydantic_ai import ModelRetry, ToolOutput

from tabulaflow.research.observability import trace_prediction
from tabulaflow.data import SQLConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter
from tabulaflow.agents.summarization import DBSummarizer
from tabulaflow.agents.llm import ReasoningLevel, ServiceTier, make_model_settings
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.types import DbtTask, DbtTaskOutput
from tabulaflow.agents.llm import make_agent

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
    reasoning: ReasoningLevel | None = None
    service_tier: ServiceTier | None = None

    def to_model_settings(self) -> dict[str, Any]:
        settings: dict[str, Any] = {}
        if self.temperature is not None:
            settings["temperature"] = self.temperature
        settings.update(
            make_model_settings(
                model=self.llm,
                reasoning=self.reasoning,
                service_tier=self.service_tier,
            )
        )
        return settings


class DbtLLMEnsembler:
    name: ClassVar[str] = "dbt_llm"

    def __init__(self, config: DbtLLMEnsemblerConfig):
        self.config = config
        self.formatter = SQLDDLSchemaFormatter()

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

    @trace_prediction
    async def ensemble_async(
        self,
        task: DbtTask,
        db_connector: SQLConnector,
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
                dbt_run_success=("unknown" if output.dbt_run_success is None else str(output.dbt_run_success).lower()),
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
                raise ModelRetry(f"Number must be between 1 and {num_candidates}.")
            return number - 1

        agent = make_agent(
            self.config.llm,
            instructions=system_prompt,
            output_type=ToolOutput(answer, name="answer"),
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(user_prompt)
        usage = Usage.from_pydantic_ai_usage(result.usage, self.config.llm)
        summary_usage = db_summarizer.usage()
        if summary_usage.api_requests:
            usage += summary_usage
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
