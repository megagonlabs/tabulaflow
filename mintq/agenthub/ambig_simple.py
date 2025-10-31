import jinja2
import time
from typing import ClassVar, Literal
from pydantic_ai import Agent
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.schema import AmbigNL2QTask, SimpleAmbigNL2QTaskOutput, PredQuery, Usage, Trajectory
from mintq.toolhub import (
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    AskUserTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.agenthub.base import agent_registry, BaseUserSimulator, BaseAgentConfig
from mintq.agenthub.utils import get_max_steps_processor, instrument, BasicAgentConfig
from mintq.metadata_synthesizers import SchemaCompressor


SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- The question has one or multiple ambiguity points and you will need to ask the user to resolve the ambiguity.
  - You are allowed to ask multiple times but only ask one question about one ambiguity point at a time. 
- Do not repeat the question if user refused to answer it.
- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions.
- Adhere strictly to the given database schema when constructing queries.
""".strip()


class AmbigSimpleSQLAgentConfig(BasicAgentConfig):
    user_patience: int | Literal["NUM_AMBIG_POINTS"] | None = None


@agent_registry.register
class AmbigSimpleSQLAgent:
    name: ClassVar = "ambig_simple_sql_agent"
    task_type: ClassVar = "ambig"
    output_type: ClassVar = "ambig-simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = AmbigSimpleSQLAgentConfig

    def __init__(
        self,
        config: AmbigSimpleSQLAgentConfig,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()
        self.compressor = SchemaCompressor() if config.compress_schema else None

    @classmethod
    async def from_config_async(cls, config: AmbigSimpleSQLAgentConfig) -> "AmbigSimpleSQLAgent":
        return cls(config)

    @instrument
    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> SimpleAmbigNL2QTaskOutput:
        t0 = time.time()

        if self.config.user_patience == "NUM_AMBIG_POINTS":
            user_patience = len(task.gold_ambiguity_points)
        else:
            user_patience = self.config.user_patience

        tools: dict[str, BaseTool] = {
            "get_schema": GetSchemaTool(db_connector.schema, self.formatter, self.compressor),
            "get_column_description": GetColumnDescriptionTool(db_connector),
            "ask_user": AskUserTool(user_simulator, patience=user_patience),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }

        agent = Agent[None, PredQuery](  # type: ignore
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=jinja2.Template(SYSTEM_PROMPT).render(language=task.language),
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings={"temperature": self.config.temperature},
        )

        result = await agent.run(task.question)
        pred_query: PredQuery = result.output
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages())

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}  # type: ignore

        return SimpleAmbigNL2QTaskOutput(
            **task.model_dump(),
            pred_intended_query=pred_query,
            trajectory=[trajectory, user_simulator.trajectory()],
            usage=Usage.from_pydantic_ai_usage(result.usage(), self.config.llm),
            user_simulator_usage=user_simulator.usage(),
            inference_metrics=metrics,
        )
