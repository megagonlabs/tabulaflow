import asyncio
import logging
from typing import Any, ClassVar

import jinja2
from pydantic import BaseModel
from pydantic_ai import Agent, ToolOutput

from mintq.agenthub.base import BaseAgentConfig
from mintq.agenthub.utils import instrument
from mintq.db_connector import BaseSQLDBConnector
from mintq.pipelines.populate_exec_results import populate_task_async
from mintq.preprocessors import DBSummarizer
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, Usage, Trajectory


logger = logging.getLogger(__name__)

_DF_PREVIEW_MAX_ROWS = 10

LLM_ENSEMBLE_SYSTEM_PROMPT = """
You are a helpful AI database expert. You are given a natural-language question and multiple candidate SQL queries along with their execution results.

Your task is to select the **single best** candidate whose SQL query most accurately answers the question.

<guidelines>
- The correct query should faithfully reflect the question without adding or omitting conditions.
- Prefer candidates whose execution results are non-empty and look reasonable for the question asked.
- If multiple candidates produce identical results, prefer the one with the simpler / more readable query.
- If all candidates look equally plausible, prefer the first one.
- If no candidate looks correct, still pick the best available one.
</guidelines>
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
{%- if task_document %}

<task_document>
{{ task_document }}
</task_document>
{%- endif %}
""".strip()

CANDIDATE_TEMPLATE = """
<candidate number="{{ number }}">
<sql>
{{ sql }}
</sql>
<execution_result>
{{ exec_result }}
</execution_result>
</candidate>
""".strip()

USER_PROMPT_TEMPLATE = """
Question: {{ question }}
{%- if question_instructions %}
{{ question_instructions }}
{%- endif %}

Here are the candidate SQL queries and their execution results:

{% for candidate in candidates %}
{{ candidate }}
{% endfor %}

Select the number of the best candidate.
""".strip()


class LLMEnsemblerConfig(BaseModel):
    result_dirs: list[str]
    llm: str = "openai-responses:gpt-5-mini"
    db_summarizer_llm: str = "openai-responses:gpt-5.4"
    skip_empty_results: bool = True
    temperature: float | None = None
    openai_reasoning_effort: str | None = None
    openai_service_tier: str | None = None

    def to_model_settings(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if self.temperature is not None:
            res["temperature"] = self.temperature
        if self.openai_reasoning_effort is not None:
            res["openai_reasoning_effort"] = self.openai_reasoning_effort
        if self.openai_service_tier is not None:
            res["openai_service_tier"] = self.openai_service_tier
        return res


class LLMEnsembler:
    name: ClassVar = "llm_ensembler"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = LLMEnsemblerConfig

    def __init__(self, config: LLMEnsemblerConfig):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: LLMEnsemblerConfig) -> "LLMEnsembler":
        return cls(config)

    def _format_exec_result(self, output: SimpleNL2QTaskOutput) -> str:
        """Format the execution result of a candidate for the LLM prompt."""
        if output.pred_query is None:
            return "(no query)"
        exec_result = output.pred_query.exec_result
        if exec_result is None:
            return "(not executed)"
        if exec_result.error is not None:
            return f"ERROR: {exec_result.error.message}"
        if exec_result.df is None:
            return "(no result)"
        if exec_result.df.empty:
            return "(empty result)"
        df = exec_result.df
        preview: str = df.head(_DF_PREVIEW_MAX_ROWS).to_string(index=False)
        suffix = ""
        if len(df) > _DF_PREVIEW_MAX_ROWS:
            suffix = f"\n... ({len(df)} rows total, showing first {_DF_PREVIEW_MAX_ROWS})"
        return preview + suffix

    @instrument
    async def ensemble_async(
        self,
        task: SimpleNL2QTask,
        db_connector: BaseSQLDBConnector,
        task_outputs: list[SimpleNL2QTaskOutput],
    ) -> SimpleNL2QTaskOutput:
        # Filter to outputs that have a pred_query
        candidates = [output for output in task_outputs if output.pred_query is not None]

        if not candidates:
            return task_outputs[0]

        # Populate exec results for all candidates (skips queries that already have results)
        await asyncio.gather(*[populate_task_async(output, db_connector) for output in candidates])

        # Filter out candidates with execution errors
        candidates = [
            output for output in candidates if output.pred_query.exec_result.df is not None  # type: ignore[union-attr]
        ]
        # Optionally also filter out candidates with empty results
        if self.config.skip_empty_results:
            candidates = [
                output for output in candidates if not output.pred_query.exec_result.df.empty  # type: ignore[union-attr]
            ]

        if len(candidates) <= 1:
            best = candidates[0] if candidates else task_outputs[0]
            return SimpleNL2QTaskOutput(**task.model_dump(), pred_query=best.pred_query)

        # Get db summary for context
        db_summarizer = DBSummarizer(llm=self.config.db_summarizer_llm)
        db_summary = await db_summarizer.preprocess_async(db_connector)

        # Build candidate descriptions for the LLM
        candidate_strs: list[str] = []
        for i, output in enumerate(candidates):
            assert output.pred_query is not None
            candidate_str = jinja2.Template(CANDIDATE_TEMPLATE).render(
                number=i + 1,
                sql=output.pred_query.query,
                exec_result=self._format_exec_result(output),
            )
            candidate_strs.append(candidate_str)

        system_prompt = jinja2.Template(LLM_ENSEMBLE_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
            db_document=db_summary.db_summary_markdown,
            task_document=task.document,
        )

        user_prompt = jinja2.Template(USER_PROMPT_TEMPLATE).render(
            question=task.question,
            question_instructions=task.question_instructions,
            candidates=candidate_strs,
        )

        num_candidates = len(candidates)

        def answer(number: int) -> int:
            """
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
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-ENSEMBLE")

        best_output = candidates[result.output]

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=best_output.pred_query,
            usage=usage,
            trajectory=trajectory,
        )
