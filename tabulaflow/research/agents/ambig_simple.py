import jinja2
import time
from typing import ClassVar, Literal
from tabulaflow.data import SQLConnector
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.types import PredQuery
from tabulaflow.research.types import AmbigNL2QTask, SimpleAmbigNL2QTaskOutput, UserSimulatorProtocol
from tabulaflow.agents.tools import AgentTool, RunQueryTool
from tabulaflow.agents.tools.run_query import latest_query_execution
from tabulaflow.research.tools import (
    SearchKeywordsTool,
    FinishTool,
    AskUserTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from tabulaflow.research.agents.registry import agent_registry
from tabulaflow.research.agents.utils import get_max_steps_capability, BasicAgentConfig
from tabulaflow.agents.llm import make_agent


SYSTEM_PROMPT = """
You are a TabulaFlow agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- The question has one or multiple ambiguity points and you will need to ask the user to resolve the ambiguity.
- Do not repeat the question if user refused to answer it.
{% if user_patience -%}
- You have in total {{user_patience}} attempts to call `ask_user` tool to resolve the ambiguity.
  - Only ask one question about one ambiguity point at a time. Try to be comprehensive of all possible ambiguities.
- If the `ask_user` tool is not provided, it means you have used up all your attempts to resolve the ambiguity.
  - Do not attempt to resolve additional ambiguities with the user. Proceed to write the query with the provided information.
{% else -%}
- You are allowed to ask multiple times but only ask one question about one ambiguity point at a time. Try to be comprehensive of all possible ambiguities.
{% endif -%}
- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions.
- Adhere strictly to the given database schema when constructing queries.
- If you think the last executed query is correct, call the `finish` tool with no arguments. Do not output text.

{% if dataset_instructions -%}
=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ===
{% endif -%}
""".strip()


class AmbigSimpleSQLAgentConfig(BasicAgentConfig):
    user_patience: int | Literal["NUM_AMBIG_POINTS"] | None = None


@agent_registry.register
class AmbigSimpleSQLAgent:
    name: ClassVar[str] = "ambig_simple_sql_agent"
    task_type: ClassVar[str] = "ambig"
    output_type: ClassVar[str] = "ambig-simple"
    config_cls: ClassVar[type[AmbigSimpleSQLAgentConfig]] = AmbigSimpleSQLAgentConfig

    def __init__(
        self,
        config: AmbigSimpleSQLAgentConfig,
    ):
        self.config = config
        self.formatter = config.create_schema_formatter("sql")

    @classmethod
    async def from_config_async(cls, config: AmbigSimpleSQLAgentConfig) -> "AmbigSimpleSQLAgent":
        return cls(config)

    @trace_prediction
    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: SQLConnector, user_simulator: UserSimulatorProtocol
    ) -> SimpleAmbigNL2QTaskOutput:
        t0 = time.time()

        if self.config.user_patience == "NUM_AMBIG_POINTS":
            user_patience = len(task.gold_ambiguity_points)
        else:
            user_patience = self.config.user_patience  # type: ignore

        schema = db_connector.schema
        tools: dict[str, AgentTool] = {}
        tools["get_schema"] = GetSchemaTool(schema, self.formatter)
        if self.config.use_column_descriptions:
            tools["get_column_description"] = GetColumnDescriptionTool(schema)
        tools["ask_user"] = AskUserTool(user_simulator, patience=user_patience)
        tools["search_keywords"] = SearchKeywordsTool(db_connector)
        tools["run_query"] = RunQueryTool(db_connector, enable_params=True)
        tools["finish"] = FinishTool()

        agent = make_agent(
            self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=jinja2.Template(SYSTEM_PROMPT).render(
                language=db_connector.language,
                dataset_instructions=task.dataset_instructions,
                user_patience=user_patience,
            ),
            capabilities=[get_max_steps_capability(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )

        result = await agent.run(task.question)
        pred_query = PredQuery.from_execution(latest_query_execution(result.all_messages()))
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages())

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}  # type: ignore
        metrics["user_effort"] = user_simulator.user_effort()

        return SimpleAmbigNL2QTaskOutput(
            **task.model_dump(),
            pred_intended_query=pred_query,
            trajectory=[trajectory, user_simulator.trajectory()],
            usage=Usage.from_pydantic_ai_usage(result.usage, self.config.llm),
            user_simulator_usage=user_simulator.usage(),
            inference_metrics=metrics,
        )
