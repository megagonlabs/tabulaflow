from dataclasses import dataclass
import jinja2
import time
from typing import Any, Callable
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter, HSchemaFormatter
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, HSQLSchema
from mintq.pydantic_ai_utils import get_pydantic_ai_llm, pydantic_ai_messages_to_trajectory
from mintq.utils import extract_code, get_llm_api_cost
from mintq.toolhub import RunQueryTool, SearchKeywordsTool, FinishTool, ShowTableSectionTool, MarkRelevantColumnTool
from mintq.metadata_synthesizer import HSchemaSynthesizer


# @dataclass
# class SchemaLinkingTaskContext:
#     task: SimpleNL2QTask
#     db_connector: BaseAsyncSQLDBConnector
#     max_steps: int
#     original_hschema: HSQLSchema
#     relevant_hschema: HSQLSchema


# @dataclass
# class SchemaLinkingOutput:
#     relevant_schema: HSQLSchema


# @dataclass
# class SQLWritingTaskContext:
#     task: SimpleNL2QTask
#     db_connector: BaseAsyncSQLDBConnector
#     max_steps: int
#     relevant_schema: HSQLSchema


# @dataclass
# class SQLWritingOutput:
#     query: str | None
#     fail_reason: str | None


SCHEMA_LINKING_SYSTEM_PROMPT = """
You are a helpful assistant that can identify the relevant columns in the database schema for the given question.

- Include all columns that are relevant to the question in the final query, including primary keys and foreign keys.
""".strip()

SCHEMA_LINKING_TASK_PROMPT = """
=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===

Question: {{question}}
{% if hints %}
=== START OF HINTS ===
{{hints}}
=== END OF HINTS ===
{% endif %}
""".strip()


SQL_WRITING_SYSTEM_PROMPT = """
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


SQL_WRITING_TASK_PROMPT = """
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


def get_max_steps_reached_processor(
    max_steps: int,
) -> Callable[[RunContext[Any], list[ModelMessage]], list[ModelMessage]]:
    def _fn(
        ctx: RunContext[Any],
        messages: list[ModelMessage],
    ) -> list[ModelMessage]:
        assert messages is ctx.messages  # We want the injected message to be preserved in the message history as well
        if ctx.run_step == max_steps:
            content = "You have reached the maximum number of steps. You have one more attempt to execute the `run_query` tool with the final query and then the `finish` tool"
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        return messages

    return _fn


async def finish_schema_linking() -> None:
    return None


class SQLMultiAgentV1:
    name = "sql_multi_agent_v1"

    def __init__(
        self,
        llm: str,
        schema_formatter: BaseSQLSchemaFormatter,
        temperature: float = 0.0,
        num_candidates: int = 1,
        schema_linking_max_steps: int = 40,
        sql_writing_max_steps: int = 20,
    ):
        self.llm = llm
        self.temperature = temperature
        self.num_candidates = num_candidates
        self.schema_linking_max_steps = schema_linking_max_steps
        self.sql_writing_max_steps = sql_writing_max_steps

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

        show_table_section_tool = ShowTableSectionTool(hschema, self.hschema_formatter)
        mark_relevant_column_tool = MarkRelevantColumnTool(hschema)
        schema_linking_agent = Agent[None, None](  # type: ignore
            get_pydantic_ai_llm(self.llm),
            tools=[
                show_table_section_tool.as_pydantic_ai_tool(),
                mark_relevant_column_tool.as_pydantic_ai_tool(),
            ],
            deps_type=None,
            output_type=finish_schema_linking,
            result_tool_name="finish",
            instructions=jinja2.Template(SCHEMA_LINKING_SYSTEM_PROMPT).render(),
            history_processors=[get_max_steps_reached_processor(self.schema_linking_max_steps)],
        )

        search_keywords_tool = SearchKeywordsTool(db_connector, self.formatter)
        run_query_tool = RunQueryTool(db_connector)
        finish_tool = FinishTool()
        sql_writing_agent = Agent[None, str](  # type: ignore
            get_pydantic_ai_llm(self.llm),
            tools=[
                search_keywords_tool.as_pydantic_ai_tool(),
                run_query_tool.as_pydantic_ai_tool(),
            ],
            deps_type=None,
            output_type=finish_tool.as_pydantic_ai_tool(),
            result_tool_name="finish",
            instructions=jinja2.Template(SQL_WRITING_SYSTEM_PROMPT).render(language=task.language),
            history_processors=[get_max_steps_reached_processor(self.sql_writing_max_steps)],
        )
        agent_no_tools = Agent[None, str](
            get_pydantic_ai_llm(self.llm),
            tools=[],
            deps_type=None,
            instructions=jinja2.Template(SQL_WRITING_SYSTEM_PROMPT).render(language=task.language),
        )

        schema_linking_agent.instrument_all()
        sql_writing_agent.instrument_all()
        agent_no_tools.instrument_all()

        # Run the agent
        fallback = False
        try:
            schema_linking_prompt = jinja2.Template(SCHEMA_LINKING_TASK_PROMPT).render(
                schema=self.hschema_formatter.format(hschema, collapse_non_core_sections=True),
                hints=task.evidence,
                question=task.question,
            )
            schema_linking_result = await schema_linking_agent.run(
                schema_linking_prompt, model_settings={"temperature": self.temperature}
            )
            schema_linking_messages = schema_linking_result.all_messages()[:-1]  # Remove the output of the finish tool
            schema_linking_trajectory = pydantic_ai_messages_to_trajectory(schema_linking_messages)
            relevant_hschema = mark_relevant_column_tool.relevant_hschema
            sql_writing_prompt = jinja2.Template(SQL_WRITING_TASK_PROMPT).render(
                schema=self.hschema_formatter.format(relevant_hschema, collapse_non_core_sections=False),
                hints=task.evidence,
                question=task.question,
                language=task.language,
            )
            result = await sql_writing_agent.run(sql_writing_prompt, model_settings={"temperature": self.temperature})
            trajectory = pydantic_ai_messages_to_trajectory(result.all_messages()[:-1])
            trajectory.messages = schema_linking_trajectory.messages + trajectory.messages
        except (UsageLimitExceeded, UnexpectedModelBehavior):
            prompt = jinja2.Template(SQL_WRITING_TASK_PROMPT).render(
                schema=self.hschema_formatter.format(hschema, collapse_non_core_sections=False),
                hints=task.evidence,
                question=task.question,
                language=task.language,
            )
            result = await agent_no_tools.run(prompt, model_settings={"temperature": self.temperature})
            trajectory = pydantic_ai_messages_to_trajectory(result.all_messages())
            fallback = True
        pred_query = extract_code(result.output)

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
        metrics["show_table_section_table_not_found"] = show_table_section_tool.metrics_.error_table_not_found
        metrics["show_table_section_section_not_found"] = show_table_section_tool.metrics_.error_section_not_found
        metrics["mark_relevant_column_table_not_found"] = mark_relevant_column_tool.metrics_.error_table_not_found
        metrics["mark_relevant_column_column_not_found"] = mark_relevant_column_tool.metrics_.error_column_not_found
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
