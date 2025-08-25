from dataclasses import dataclass
import jinja2
import time
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter, HSchemaFormatter
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput
from mintq.pydantic_ai_utils import get_pydantic_ai_llm, pydantic_ai_messages_to_trajectory
from mintq.utils import extract_code, get_llm_api_cost
from mintq.toolhub import RunQueryTool, SearchKeywordsTool, FinishTool, ShowTableSectionTool
from mintq.metadata_synthesizer import HSchemaSynthesizer


@dataclass
class TaskContext:
    task: SimpleNL2QTask
    db_connector: BaseAsyncSQLDBConnector
    max_steps: int


SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Utilize the provided hints to guide query formulation.
- The final query should not return additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not return the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not return the score.
{% if language == "SnowflakeSQL" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{% endif %}
""".strip()


TASK_PROMPT = """
=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===

Question: {{question}}
{% if hints %}
=== START OF HINTS ===
{{hints}}
=== END OF HINTS ===
{% endif %}
{{language}} query:
""".strip()


def get_system_prompt(ctx: RunContext[TaskContext]) -> str:
    return jinja2.Template(SYSTEM_PROMPT).render(language=ctx.deps.task.language)


def max_steps_reached_processor(
    ctx: RunContext[TaskContext],
    messages: list[ModelMessage],
) -> list[ModelMessage]:
    assert messages is ctx.messages  # We want the injected message to be preserved in the message history as well
    if ctx.run_step == ctx.deps.max_steps:
        content = "You have reached the maximum number of steps. You have one more attempt to execute the `run_query` tool with the final query and then the `finish` tool"
        messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
    return messages


class SQLAgent:
    name = "sql_agent"

    def __init__(
        self,
        llm: str,
        schema_formatter: BaseSQLSchemaFormatter,
        temperature: float = 0.0,
        num_candidates: int = 1,
        max_steps: int = 20,
    ):
        self.llm = llm
        self.temperature = temperature
        self.num_candidates = num_candidates
        self.max_steps = max_steps

        self.formatter = schema_formatter
        self.hschema_synthesizer = HSchemaSynthesizer()
        self.hschema_formatter = HSchemaFormatter()

    def get_config(self) -> dict[str, str | int | float | bool]:
        return {
            "llm": self.llm,
            "temperature": self.temperature,
            "schema_formatter": self.formatter.name,
            "num_candidates": self.num_candidates,
        }

    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseAsyncSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        hschema = await self.hschema_synthesizer.run_async(db_connector)

        # list_columns_tool = ListColumnsTool(db_connector.schema, self.formatter)
        # show_table_section_tool = ShowTableSectionTool(hschema, self.hschema_formatter)
        search_keywords_tool = SearchKeywordsTool(db_connector)
        run_query_tool = RunQueryTool(db_connector)
        finish_tool = FinishTool()
        agent = Agent[TaskContext, str](  # type: ignore
            get_pydantic_ai_llm(self.llm),
            tools=[
                # list_columns_tool.as_pydantic_ai_tool(),
                # show_table_section_tool.as_pydantic_ai_tool(),
                search_keywords_tool.as_pydantic_ai_tool(),
                run_query_tool.as_pydantic_ai_tool(),
            ],
            deps_type=TaskContext,
            output_type=finish_tool.as_pydantic_ai_tool(),
            result_tool_name="finish",
            # result_tool_description="Finish the task and return the last executed query as final answer.",
            instructions=get_system_prompt,
            history_processors=[max_steps_reached_processor],
        )
        agent.instrument_all()

        agent_no_tools = Agent[TaskContext, str](
            get_pydantic_ai_llm(self.llm),
            tools=[],
            deps_type=TaskContext,
            instructions=get_system_prompt,
        )
        agent_no_tools.instrument_all()

        prompt = jinja2.Template(TASK_PROMPT).render(
            schema=self.hschema_formatter.format(hschema, collapse_non_core_sections=False),
            hints=task.evidence,
            question=task.question,
            language=task.language,
        )

        # Construct dependencies
        deps = TaskContext(
            task=task,
            db_connector=db_connector,
            max_steps=self.max_steps,
        )

        # Run the agent
        fallback = False
        try:
            result = await agent.run(prompt, deps=deps, model_settings={"temperature": self.temperature})
            messages = result.all_messages()[:-1]
        except (UsageLimitExceeded, UnexpectedModelBehavior):
            result = await agent_no_tools.run(prompt, deps=deps, model_settings={"temperature": self.temperature})
            messages = result.all_messages()
            fallback = True
        pred_query = extract_code(result.output)
        trajectory = pydantic_ai_messages_to_trajectory(messages)

        usage = result.usage()
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["api_calls"] = usage.requests
        metrics["input_tokens"] = usage.request_tokens if usage.request_tokens else 0
        metrics["output_tokens"] = usage.response_tokens if usage.response_tokens else 0
        metrics["api_cost_usd"] = get_llm_api_cost(self.llm, metrics["input_tokens"], metrics["output_tokens"])  # type: ignore
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["run_query_timeout"] = run_query_tool.metrics_.error_timeout
        metrics["run_query_failed"] = run_query_tool.metrics_.error_query_failed
        # metrics["show_table_section_table_not_found"] = show_table_section_tool.metrics_.error_table_not_found
        # metrics["show_table_section_section_not_found"] = show_table_section_tool.metrics_.error_section_not_found
        metrics["search_keywords_table_not_found"] = search_keywords_tool.metrics_.error_table_not_found
        metrics["search_keywords_column_not_found"] = search_keywords_tool.metrics_.error_column_not_found
        metrics["search_keywords_column_not_string"] = search_keywords_tool.metrics_.error_column_not_string
        metrics["finish_no_query_executed"] = finish_tool.metrics_.error_no_query_executed
        metrics["fallback"] = 1 if fallback else 0
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            metrics=metrics,
        )
