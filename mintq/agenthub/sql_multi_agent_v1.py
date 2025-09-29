import jinja2
import time
from typing import Any, Callable, ClassVar
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.formatters.hschema import HSchemaFormatter
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, PredQuery, Usage, Trajectory
from mintq.utils import extract_code
from mintq.toolhub import RunQueryTool, SearchKeywordsTool, FinishTool, ShowTableSectionTool, MarkRelevantColumnTool
from mintq.metadata_synthesizers import HSchemaSynthesizer
from mintq.agenthub.base import agent_registry


# @dataclass
# class SchemaLinkingTaskContext:
#     task: SimpleNL2QTask
#     db_connector: BaseSQLDBConnector
#     max_steps: int
#     original_hschema: HSQLSchemra
#     relevant_hschema: HSQLSchemra


# @dataclass
# class SchemaLinkingOutput:
#     relevant_schema: HSQLSchema


# @dataclass
# class SQLWritingTaskContext:
#     task: SimpleNL2QTask
#     db_connector: BaseSQLDBConnector
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


class SQLMultiAgentV1Config(BaseModel):
    llm: str
    schema_formatter: str
    temperature: float = 0.0
    num_candidates: int = 1
    schema_linking_max_steps: int = 40
    sql_writing_max_steps: int = 20


@agent_registry.register
class SQLMultiAgentV1:
    name: ClassVar = "sql_multi_agent_v1"
    config_cls: ClassVar = SQLMultiAgentV1Config

    def __init__(
        self,
        config: SQLMultiAgentV1Config,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()  # type: ignore
        self.hschema_synthesizer = HSchemaSynthesizer()
        self.hschema_formatter = HSchemaFormatter()

    @classmethod
    async def from_config_async(cls, config: SQLMultiAgentV1Config) -> "SQLMultiAgentV1":
        return cls(config)

    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        hschema = await self.hschema_synthesizer.run_async(db_connector)

        show_table_section_tool = ShowTableSectionTool(hschema, self.hschema_formatter)
        mark_relevant_column_tool = MarkRelevantColumnTool(hschema)
        schema_linking_agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[
                show_table_section_tool.as_pydantic_ai_tool(),
                mark_relevant_column_tool.as_pydantic_ai_tool(),
            ],
            deps_type=None,
            output_type=finish_schema_linking,
            result_tool_name="finish",
            instructions=jinja2.Template(SCHEMA_LINKING_SYSTEM_PROMPT).render(),
            history_processors=[get_max_steps_reached_processor(self.config.schema_linking_max_steps)],
        )

        search_keywords_tool = SearchKeywordsTool(db_connector)
        run_query_tool = RunQueryTool(db_connector)
        finish_tool = FinishTool()
        all_tools = [
            show_table_section_tool,
            mark_relevant_column_tool,
            search_keywords_tool,
            run_query_tool,
            finish_tool,
        ]

        sql_writing_agent = Agent[None, str](  # type: ignore
            model=self.config.llm,
            tools=[
                search_keywords_tool.as_pydantic_ai_tool(),
                run_query_tool.as_pydantic_ai_tool(),
            ],
            deps_type=None,
            output_type=finish_tool.as_pydantic_ai_tool(),
            result_tool_name="finish",
            instructions=jinja2.Template(SQL_WRITING_SYSTEM_PROMPT).render(language=task.language),
            history_processors=[get_max_steps_reached_processor(self.config.sql_writing_max_steps)],
        )
        agent_no_tools = Agent[None, str](  # type: ignore
            model=self.config.llm,
            tools=[],
            deps_type=None,
            instructions=jinja2.Template(SQL_WRITING_SYSTEM_PROMPT).render(language=task.language),
        )

        all_tools = [
            show_table_section_tool,
            mark_relevant_column_tool,
            search_keywords_tool,
            run_query_tool,
            finish_tool,
        ]

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
                schema_linking_prompt, model_settings={"temperature": self.config.temperature}
            )
            schema_linking_messages = schema_linking_result.all_messages()[:-1]  # Remove the output of the finish tool
            schema_linking_trajectory = Trajectory.from_pydantic_ai_messages(schema_linking_messages)
            relevant_hschema = mark_relevant_column_tool.relevant_hschema
            sql_writing_prompt = jinja2.Template(SQL_WRITING_TASK_PROMPT).render(
                schema=self.hschema_formatter.format(relevant_hschema, collapse_non_core_sections=False),
                hints=task.evidence,
                question=task.question,
                language=task.language,
            )
            result = await sql_writing_agent.run(
                sql_writing_prompt, model_settings={"temperature": self.config.temperature}
            )
            trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages()[:-1])
            trajectory.messages = schema_linking_trajectory.messages + trajectory.messages
        except (UsageLimitExceeded, UnexpectedModelBehavior):
            prompt = jinja2.Template(SQL_WRITING_TASK_PROMPT).render(
                schema=self.hschema_formatter.format(hschema, collapse_non_core_sections=False),
                hints=task.evidence,
                question=task.question,
                language=task.language,
            )
            result = await agent_no_tools.run(prompt, model_settings={"temperature": self.config.temperature})
            trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages())
            fallback = True
        pred_query = PredQuery(query=extract_code(result.output))

        usages = [Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)]

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["api_cost_usd"] = sum(usage.api_cost_usd for usage in usages)
        metrics["input_tokens"] = sum(usage.input_tokens for usage in usages)
        metrics["output_tokens"] = sum(usage.output_tokens for usage in usages)
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["fallback"] = fallback
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {tool.name: tool.get_metrics().model_dump() for tool in all_tools}  # type: ignore

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            usages=usages,
            inference_metrics=metrics,
        )
