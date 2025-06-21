from dataclasses import dataclass
import jinja2
import time
import json
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.usage import Usage
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, SQLTableSchema
from mintq.modelhub.pydantic_ai_utils import get_pydantic_ai_llm, pydantic_ai_messages_to_trajectory
from mintq.utils import extract_code, get_llm_api_cost
from mintq.toolhub import RunQueryTool, ListColumnsTool, SearchKeywordsTool


@dataclass
class TaskContext:
    task: SimpleNL2QTask
    db_connector: BaseAsyncSQLDBConnector
    formatter: BaseSQLSchemaFormatter
    table_id_to_schema: dict[str, SQLTableSchema]
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
Question: {{question}}
{% if hints %}
=== START OF HINTS ===
{{hints}}
=== END OF HINTS ===
{% endif %}
=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===

{{language}} query:
""".strip()


def get_system_prompt(ctx: RunContext[TaskContext]) -> str:
    return jinja2.Template(SYSTEM_PROMPT).render(language=ctx.deps.task.language)


def add_max_steps_reached(ctx: RunContext[TaskContext], res: str) -> str:
    if ctx.usage.requests == ctx.deps.max_steps:
        res += "\n(Warning: You have reached the maximum number of steps. You have one more attempt to execute the `run_query` tool with the final query and then the `finish` tool)"
    return res


def finish(ctx: RunContext[TaskContext]) -> str:
    """
    Finish the task and return the last executed query as final answer.
    """
    for msg in ctx.messages[::-1]:
        if msg.kind == "response":
            for part in msg.parts[::-1]:
                if part.part_kind == "tool-call" and part.tool_name == "run_query":
                    if isinstance(part.args, str):
                        return json.loads(part.args)["query"]  # type: ignore
                    elif isinstance(part.args, dict):
                        return part.args["query"]  # type: ignore
                    else:
                        raise ValueError(f"Unexpected tool call argument type: {type(part.args)}")
    ctx.usage.incr(Usage(details={"finish_no_query_executed": 1}))
    raise ModelRetry("No query has been executed, you cannot finish yet")


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

    def get_config(self) -> dict[str, str | int | float | bool]:
        return {
            "llm": self.llm,
            "temperature": self.temperature,
            "schema_formatter": self.formatter.name,
            "num_candidates": self.num_candidates,
        }

    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseAsyncSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        list_columns_tool = ListColumnsTool(db_connector.schema, self.formatter)
        search_keywords_tool = SearchKeywordsTool(db_connector, self.formatter)
        run_query_tool = RunQueryTool(db_connector)

        agent = Agent[TaskContext, str](  # type: ignore
            get_pydantic_ai_llm(self.llm),
            tools=[
                list_columns_tool.as_pydantic_ai_tool(),
                search_keywords_tool.as_pydantic_ai_tool(),
                run_query_tool.as_pydantic_ai_tool(),
            ],
            deps_type=TaskContext,
            output_type=finish,
            result_tool_name="finish",
            result_tool_description="Finish the task and return the last executed query as final answer.",
            instructions=get_system_prompt,
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
            schema=self.formatter.format(db_connector.schema, pk_fk_column_only=True),
            hints=task.evidence,
            question=task.question,
            language=task.language,
        )

        # Construct dependencies
        table_id_to_schema = {self.formatter.format_table_name(table): table for table in db_connector.schema.tables}
        deps = TaskContext(
            task=task,
            db_connector=db_connector,
            formatter=self.formatter,
            table_id_to_schema=table_id_to_schema,
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
        metrics["list_columns_table_not_found"] = list_columns_tool.metrics_["list_columns_table_not_found"]
        metrics["search_keywords_table_not_found"] = search_keywords_tool.metrics_["search_keywords_table_not_found"]
        metrics["search_keywords_column_not_found"] = search_keywords_tool.metrics_["search_keywords_column_not_found"]
        metrics["search_keywords_column_not_string"] = search_keywords_tool.metrics_[
            "search_keywords_column_not_string"
        ]
        metrics["finish_no_query_executed"] = usage.details.get("finish_no_query_executed", 0)
        metrics["fallback"] = 1 if fallback else 0
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            metrics=metrics,
        )
