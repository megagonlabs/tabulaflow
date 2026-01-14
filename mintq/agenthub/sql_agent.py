import copy
import jinja2
import time
from typing import ClassVar
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, PredQuery, Usage, Trajectory
from mintq.utils import extract_code
from mintq.metadata_synthesizers import SchemaCompressor
from mintq.toolhub import (
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import get_max_steps_processor, instrument, BasicAgentConfig, TaskRunContext


SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- When there is a conflict between instructions, prioritize the question and hints provided by the user.
{% if language == "SnowflakeSQL" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{% endif %}

{% if dataset_instructions %}=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ==={% endif %}
""".strip()


PARSE_QUESTION_PROMPT = """
You are a helpful AI database expert who can analyze a given text-to-SQL question and identify the specific information pieces that must appear in the final result table.

- The output should be an ordered list of information piece descriptions.
- The information pieces must correspond exactly to the columns that should appear in the final table.
- If an information piece is ambiguous and could map to multiple columns, explicitly mention this in its description.
- To decide which information pieces are required, strictly follow the dataset instructions.

=== START OF EXAMPLES ===
Input: Which 3 students with a GPA below 2.5 are performing the worst in the Math course? Include the age.
Output: ["student name or id", "student age"]
=== END OF EXAMPLES ===

=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ===

Text-to-SQL question: {{question}}
Your output:
""".strip()


POSTPROCESS_PROMPT = """
You are a helpful AI database expert who can refine a given {{language}} query to ensure it strictly follows the question and provided dataset instructions.
- The revised query must return exactly the required columns and comply with the question and all dataset constraints.
- You can remove, add, modify, or reorder columns in the query to comply with the dataset instructions.
- Do not modify the parameters in the query, if parameters are present.
- Do not modify the core logic of the query unless it conflicts with the question or dataset instructions.
- If no changes are needed, return the original query unchanged.

=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ===

Text-to-SQL Question: {{question}}

Exact Columns Required:
{{information_pieces}}

Current {{language}} Query:
{{query_readable_with_exec_results}}

Your revised {{language}} Query:
""".strip()


class Postprocessor:
    def __init__(self, config: BasicAgentConfig):
        self.config = config

    async def parse_question_async(self, ctx: TaskRunContext) -> list[str]:
        class LLMOutput(BaseModel):
            information_pieces: list[str]

        agent = Agent[None, LLMOutput](  # type: ignore
            model=self.config.llm,
            output_type=LLMOutput,
            model_settings=self.config.to_model_settings(),
        )
        prompt = jinja2.Template(PARSE_QUESTION_PROMPT).render(
            dataset_instructions=ctx.task.dataset_instructions, question=ctx.task.question
        )
        result = await agent.run(prompt)
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-PARSE-QUESTION"))
        return result.output.information_pieces

    async def postprocess_async(self, ctx: TaskRunContext, pred_query: PredQuery) -> PredQuery:
        if not ctx.task.dataset_instructions:
            return pred_query

        information_pieces = await self.parse_question_async(ctx)
        agent = Agent[None, str](  # type: ignore
            model=self.config.llm,
            model_settings=self.config.to_model_settings(),
        )
        prompt = jinja2.Template(POSTPROCESS_PROMPT).render(
            language=ctx.task.language,
            question=f"{ctx.task.question} {ctx.task.evidence}",
            dataset_instructions=ctx.task.dataset_instructions,
            information_pieces=information_pieces,
            query_readable_with_exec_results=pred_query.to_readable(),
        )
        result = await agent.run(prompt)

        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-POSTPROCESS"))

        pred_query = copy.deepcopy(pred_query)
        pred_query.query = result.output
        return pred_query


@agent_registry.register
class SQLAgent:
    name: ClassVar = "sql_agent"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = BasicAgentConfig

    def __init__(self, config: BasicAgentConfig):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()
        self.compressor = SchemaCompressor() if config.compress_schema else None
        self.postprocessor = Postprocessor(config)

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "SQLAgent":
        return cls(config)

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        ctx = TaskRunContext(task, db_connector, Usage.create(llm=self.config.llm))

        tools: dict[str, BaseTool] = {
            "get_schema": GetSchemaTool(db_connector.schema, self.formatter, self.compressor),
            "get_column_description": GetColumnDescriptionTool(db_connector),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }
        system_prompt = jinja2.Template(SYSTEM_PROMPT).render(
            language=task.language, dataset_instructions=task.dataset_instructions
        )

        agent = Agent[None, PredQuery](  # type: ignore
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )
        prompt = f"{task.question} {task.evidence}"
        result = await agent.run(prompt)
        pred_query: PredQuery = result.output
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-SQL")
        ctx.trajectories.append(trajectory)

        pred_query = await self.postprocessor.postprocess_async(ctx, pred_query)

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}  # type: ignore

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=ctx.trajectories,
            usage=ctx.usage,
            inference_metrics=metrics,
        )
