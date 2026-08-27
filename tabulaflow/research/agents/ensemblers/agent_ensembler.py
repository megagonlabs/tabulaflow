import asyncio
import logging
import time
from typing import Any, ClassVar, cast

import jinja2
from pydantic_ai import ModelRetry, RunContext, ToolOutput

from tabulaflow.research.agents.registry import AgentConfig
from tabulaflow.research.agents.ensemblers.majority_ensembler import _normalize_value
from tabulaflow.research.agents.utils import BasicAgentConfig, get_max_steps_capability, instrument
from tabulaflow.data import SQLConnectorProtocol
from tabulaflow.output.formatting import SQLSchemaFormatter, format_dataframe, schema_formatter_registry
from tabulaflow.research.execution import populate_task_exec_results
from tabulaflow.agents.summarization import DBSummarizer
from tabulaflow.agents.trace import Trajectory, Usage
from tabulaflow.research.types import PredQuery, SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.agents.tools import AgentTool, GetColumnJsonSchemaTool, GetTableSchemaTool, RunQueryTool
from tabulaflow.agents.tools.run_query import latest_query_execution
from tabulaflow.agents.llm import make_agent


logger = logging.getLogger(__name__)

_DF_PREVIEW_MAX_ROWS = 10

AGENT_ENSEMBLE_SYSTEM_PROMPT = """
You are a helpful AI database expert that writes {{language}} queries given a user question.

You are an agent given a natural-language question and multiple candidate SQL queries along with their execution results.
Your task is to either select the **single best** candidate or **write a revised/new query** that most accurately answers the question.
The correct query should faithfully reflect the question and dataset instructions without adding or omitting conditions.

You are an agent - please keep going until you are confident in your answer. Only finish your turn when you are sure the problem is solved. Autonomously resolve the task to the best of your ability.

<goal>
- Analyze the candidate queries and their execution results carefully.
- Use the available tools to inspect the database schema and verify query correctness if needed.
- You may either:
  1. Select an existing candidate if you determine it is correct, by calling finish(candidate_number=N).
  2. Write and execute a revised/new query if none of the candidates are satisfactory, then call finish() without a candidate number. The last executed query will be used as the final answer.
- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information and follow the most natural interpretation.
- Ensure the query accurately reflects the original question without adding or omitting any conditions.
- Adhere strictly to the given database schema when constructing queries.
- Pay close attention to detail.
  - When multiple similar columns or JSON fields exist, carefully select the one that best matches the question and the instructions.
  - When applying filters, if multiple columns are semantically equivalent, prefer the one that is more reliable and contains fewer null values.
- Follow the dataset and question instructions if they are provided. When there is a conflict between instructions, prioritize the question instructions.
</goal>

<tool_calling>
Gathering information:
- You may use the `get_table_schema` tool to get the schema of the relevant tables.
- You may use the `get_column_json_schema` tool to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to execute and verify queries.

Finishing:
- Call finish(candidate_number=N) to select candidate N as the best answer.
- Call finish() (without a candidate number) to use the last executed query as the final answer. You must have executed at least one query via `run_query` before finishing without a candidate number.
- For complex queries with multiple CTEs, build incrementally: execute and verify each CTE's output before adding the next. Do NOT jump straight to the full assembled query.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{dataset_instructions}}
</dataset_instructions>
{%- endif %}
{%- if db_document %}

<db_document>
{{db_document}}
</db_document>
{%- endif %}
{%- if task_document %}

<task_document>
{{task_document}}
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

Analyze the candidates and either select the best one or write a revised query.
""".strip()


class AgentEnsemblerConfig(BasicAgentConfig):
    """Config for agent-based ensembler that combines LLM ensemble with agent tools."""

    result_dirs: list[str]
    db_summarizer_llm: str = "openai-responses:gpt-5.4"
    skip_empty_results: bool = True
    deduplicate_results: bool = True


class AgentEnsembler:
    name: ClassVar = "agent_ensembler"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[AgentConfig]] = AgentEnsemblerConfig

    def __init__(self, config: AgentEnsemblerConfig):
        self.config = config
        self.formatter = cast(
            SQLSchemaFormatter,
            schema_formatter_registry.get_class(config.schema_formatter)(**config.to_formatter_kwargs()),
        )

    @classmethod
    async def from_config_async(cls, config: AgentEnsemblerConfig) -> "AgentEnsembler":
        return cls(config)

    def _format_exec_result(self, output: SimpleNL2QTaskOutput) -> str:
        """Format the execution result of a candidate for the prompt."""
        assert output.pred_query is not None and output.pred_query.exec_result is not None
        exec_result = output.pred_query.exec_result
        assert exec_result.df is not None
        if exec_result.df.empty:
            return "(empty result)"
        df = exec_result.df
        preview = format_dataframe(df, max_visible_rows=_DF_PREVIEW_MAX_ROWS)
        preview += f"\n({len(df)} rows)"
        return preview

    @instrument
    async def ensemble_async(
        self,
        task: SimpleNL2QTask,
        db_connector: SQLConnectorProtocol,
        task_outputs: list[SimpleNL2QTaskOutput],
    ) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        # Filter to outputs that have a pred_query
        candidates = [output for output in task_outputs if output.pred_query is not None]

        if not candidates:
            return task_outputs[0]

        # Populate exec results for all candidates (skips queries that already have results)
        await asyncio.gather(*[populate_task_exec_results(output, db_connector) for output in candidates])

        # Filter out candidates with execution errors
        candidates = [
            output
            for output in candidates
            if output.pred_query.exec_result.df is not None  # type: ignore[union-attr]
        ]
        # Optionally filter out candidates with empty results
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
                df = df.reindex(sorted(df.columns), axis=1)
                rows = [tuple(_normalize_value(v) for v in row) for row in df.itertuples(index=False, name=None)]
                hashable = tuple(sorted(set(rows)))
                if hashable not in seen:
                    seen.add(hashable)
                    deduped.append(output)
            candidates = deduped

        if len(candidates) <= 1:
            best = candidates[0] if candidates else task_outputs[0]
            return SimpleNL2QTaskOutput(**task.model_dump(), pred_query=best.pred_query)

        # Get db summary for context
        db_summarizer = DBSummarizer(llm=self.config.db_summarizer_llm)
        db_summary = await db_summarizer.summarize(db_connector)

        # Build candidate descriptions
        candidate_strs: list[str] = []
        for i, output in enumerate(candidates):
            assert output.pred_query is not None
            candidate_str = jinja2.Template(CANDIDATE_TEMPLATE).render(
                number=i + 1,
                sql=output.pred_query.query,
                exec_result=self._format_exec_result(output),
            )
            candidate_strs.append(candidate_str)

        system_prompt = jinja2.Template(AGENT_ENSEMBLE_SYSTEM_PROMPT).render(
            language=db_connector.language,
            dataset_instructions=task.dataset_instructions,
            db_document=db_summary,
            task_document=task.document,
        )

        user_prompt = jinja2.Template(USER_PROMPT_TEMPLATE).render(
            question=task.question,
            question_instructions=task.question_instructions,
            candidates=candidate_strs,
        )

        run_query_tool = RunQueryTool(db_connector)
        tools: dict[str, AgentTool] = {
            "get_table_schema": GetTableSchemaTool(
                db_connector,
                self.formatter,
                include_descriptions=self.config.use_column_descriptions,
            ),
            "get_column_json_schema": GetColumnJsonSchemaTool(db_connector.schema),
            "run_query": run_query_tool,
        }

        num_candidates = len(candidates)

        def finish(ctx: RunContext, candidate_number: int | None = None) -> int | None:
            """Finish the task.

            Either select an existing candidate by number, or finish with the last
            executed query as the final answer.

            Args:
                candidate_number: The 1-indexed number of the candidate to select.
                    If None, the last executed query (via run_query) will be used
                    as the final answer.
            """
            if candidate_number is not None:
                if candidate_number < 1 or candidate_number > num_candidates:
                    raise ModelRetry(
                        f"Invalid candidate_number {candidate_number}. Must be between 1 and {num_candidates}."
                    )
                return candidate_number

            # No candidate selected — require at least one run_query call
            trajectory = Trajectory.from_pydantic_ai_messages(ctx.messages)
            for msg in trajectory.messages[::-1]:
                if msg.role == "assistant":
                    for tool_call in msg.tool_calls[::-1]:
                        if tool_call.name == "run_query" and tool_call.arguments is not None:
                            return None
            raise ModelRetry(
                "No candidate selected and no query has been executed. "
                "Either call finish(candidate_number=N) to select a candidate, "
                "or execute a query via run_query first."
            )

        agent = make_agent(
            self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for tool in tools.values()],
            output_type=ToolOutput(finish, name="finish"),
            instructions=system_prompt,
            capabilities=[get_max_steps_capability(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )

        result = await agent.run(user_prompt)
        usage = Usage.from_pydantic_ai_usage(result.usage, self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-ENSEMBLE")

        chosen = result.output
        if chosen is not None:
            # Agent selected a candidate
            best_output = candidates[chosen - 1]
            pred_query = best_output.pred_query
        else:
            # Agent wrote a new/revised query
            pred_query = PredQuery.from_execution(latest_query_execution(result.all_messages()))

        metrics: dict[str, Any] = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}
        metrics["selected_candidate"] = chosen

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            usage=usage,
            trajectory=trajectory,
            inference_metrics=metrics,
        )
