import asyncio
from typing import Any, ClassVar

import jinja2
from pydantic import BaseModel
from pydantic_ai import ModelRetry, ToolOutput

from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.agents.ensemblers.utils import execution_result_key, format_execution_result
from tabulaflow.data import SQLConnector
from tabulaflow.research.query_execution import populate_query_exec_result
from tabulaflow.agents.summarization import DataSourceSummarizer
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.agents.llm import ReasoningLevel, ServiceTier, make_agent, make_model_settings


LLM_ENSEMBLE_SYSTEM_PROMPT = """
You are a helpful AI database expert.
You are given a natural-language question and multiple candidate SQL queries along with their execution results.
Your task is to select the **single best** candidate whose SQL query most accurately answers the question.
The correct query should faithfully reflect the question and dataset instructions without adding or omitting conditions.

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
    llm: str = "openai:gpt-5.6-luna"
    db_summarizer_llm: str = "openai:gpt-5.6-sol"
    skip_empty_results: bool = True
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


class LLMEnsembler:
    name: ClassVar[str] = "llm"

    def __init__(self, config: LLMEnsemblerConfig):
        self.config = config

    @trace_prediction
    async def ensemble_async(
        self,
        task: SimpleNL2QTask,
        db_connector: SQLConnector,
        task_outputs: list[SimpleNL2QTaskOutput],
    ) -> SimpleNL2QTaskOutput:
        # Filter to outputs that have a pred_query
        candidates = [output for output in task_outputs if output.pred_query is not None]

        if not candidates:
            return task_outputs[0]

        await asyncio.gather(
            *(
                populate_query_exec_result(output.pred_query, db_connector)
                for output in candidates
                if output.pred_query is not None
            )
        )

        # Filter out candidates with execution errors
        candidates = [
            output
            for output in candidates
            if output.pred_query.exec_result.df is not None  # type: ignore[union-attr]
        ]
        # Optionally also filter out candidates with empty results
        if self.config.skip_empty_results:
            candidates = [
                output
                for output in candidates
                if not output.pred_query.exec_result.df.empty  # type: ignore[union-attr]
            ]

        # Optionally deduplicate candidates with identical execution results
        if self.config.deduplicate_results:
            seen: set[tuple[tuple[str, ...], ...]] = set()
            deduped: list[SimpleNL2QTaskOutput] = []
            for output in candidates:
                df = output.pred_query.exec_result.df  # type: ignore[union-attr]
                assert df is not None
                result_key = execution_result_key(df)
                if result_key not in seen:
                    seen.add(result_key)
                    deduped.append(output)
            candidates = deduped

        if len(candidates) <= 1:
            best = candidates[0] if candidates else task_outputs[0]
            return SimpleNL2QTaskOutput(**task.model_dump(), pred_query=best.pred_query)

        # Get db summary for context
        db_summarizer = DataSourceSummarizer(llm=self.config.db_summarizer_llm)
        db_summary = await db_summarizer.summarize(db_connector)

        # Build candidate descriptions for the LLM
        candidate_strs: list[str] = []
        for i, output in enumerate(candidates):
            assert output.pred_query is not None
            candidate_str = jinja2.Template(CANDIDATE_TEMPLATE).render(
                number=i + 1,
                sql=output.pred_query.query,
                exec_result=format_execution_result(output.pred_query.exec_result.df),  # type: ignore[union-attr]
            )
            candidate_strs.append(candidate_str)

        system_prompt = jinja2.Template(LLM_ENSEMBLE_SYSTEM_PROMPT).render(
            dataset_instructions=task.dataset_instructions,
            db_document=db_summary,
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
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-ENSEMBLE")

        best_output = candidates[result.output]

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=best_output.pred_query,
            usage=usage,
            trajectory=trajectory,
        )
