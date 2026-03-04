import jinja2
import time
from typing import ClassVar
from pydantic_ai import Agent
import logging
from mintq.db_connector import BaseSQLDBConnector, NL2QDBConnector
from mintq.schema import (
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
    PredQuery,
    Usage,
    Trajectory,
)
from mintq.preprocessors import DBSummarizer, SchemaCompressor
from mintq.toolhub import (
    BaseTool,
    GetTableSchemaTool,
    RunQueryNoParamsTool,
    FinishTool,
)
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import (
    get_max_steps_processor,
    instrument,
    BasicAgentConfig,
)


logger = logging.getLogger(__name__)


class MintqAgentConfig(BasicAgentConfig):
    db_summarizer_llm: str = "openai-responses:gpt-5-mini"


def format_question(task: SimpleNL2QTask) -> str:
    res = task.question
    if task.question_instructions:
        res += "\n" + task.question_instructions
    return res


MINTQ_AGENT_SYSTEM_PROMPT = """
You a helpful AI database expert that writes {{language}} queries given a user question.

You are an agent - please keep going until the database query is fully constructed and the execution result is correct, before finishing. Only finish your turn when you are sure that the problem is solved. Autonomously resolve the task to the best of your ability.

<goal>
- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information and follow the most natural interpretation.
- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Pay close attention to detail. When multiple similar columns exist, select the one that best matches the question and the instructions.
- Follow the dataset and question instructions if they are provided. When there is a conflict between instructions, prioritize the question instructions.
</goal>

<tool_calling>
- Always use the `get_table_schema` tool to get the schema of the relevant tables before constructing the query.
- You may call the `run_query` tool multiple times while building the final query.
- You may execute intermediate or exploratory queries; however, the final query (the last one executed) must be complete and fully constructed. In the final query, do not split the logic into multiple dependent queries (for example, first retrieving an ID and then using that ID in a subsequent query—this is not allowed).
- Be THOROUGH when constructing the final query. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{dataset_instructions}}
</dataset_instructions>
{%- endif %}

<db_summary>
{{db_summary}}
</db_summary>
{%- if document %}

<document>
{{document}}
</document>
{%- endif %}
""".strip()


@agent_registry.register
class MintqAgent:
    name: ClassVar = "mintq_agent"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = MintqAgentConfig

    def __init__(
        self,
        config: MintqAgentConfig,
    ):
        self.config = config
        self.compressor = SchemaCompressor() if config.compress_schema else None

        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)(
            **config.to_formatter_kwargs()
        )

    @classmethod
    async def from_config_async(cls, config: MintqAgentConfig) -> "MintqAgent":
        return cls(config)

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: NL2QDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        db_summarizer = DBSummarizer(llm=self.config.db_summarizer_llm)

        db_summary = await db_summarizer.preprocess_async(db_connector)
        system_prompt = jinja2.Template(MINTQ_AGENT_SYSTEM_PROMPT).render(
            language=task.language,
            dataset_instructions=task.dataset_instructions,
            db_summary=db_summary.db_summary_markdown,
            document=task.document,
        )
        tools: dict[str, BaseTool] = {
            "get_table_schema": GetTableSchemaTool(db_connector, self.formatter),
            "run_query": RunQueryNoParamsTool(db_connector),
            "finish": FinishTool(),
        }

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(format_question(task))
        pred_query: PredQuery = tools["run_query"].last_pred_query()  # type: ignore
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-SQL")

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}  # type: ignore

        return SimpleNL2QTaskOutput(
            **task.model_dump(), pred_query=pred_query, trajectory=trajectory, usage=usage, inference_metrics=metrics
        )
