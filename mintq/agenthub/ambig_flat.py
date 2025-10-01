import asyncio
from dataclasses import dataclass
from functools import partial
import jinja2
import time
from typing import ClassVar
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from regex.regex import T
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.schema import AmbigNL2QTask, FlatAmbigNL2QTaskOutput, PredQuery, Usage, Trajectory
from mintq.utils import extract_code
from mintq.toolhub import (
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.agenthub.base import agent_registry, BaseUserSimulator, UserMultipleChoiceQuestion
from mintq.metadata_synthesizers import SchemaCompressor


DISAMBIGUATION_PROMPT = """
You are MintQ agent, a helpful AI database expert that can disambiguate questions about a {{language}} database.
Given an ambiguous question, you need to output the list of all possible interpretations.
Do not resolve threshold-like ambiguities where the number of interpretations is infinite.
""".strip()


TEXT2SQL_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- The question is ambiguous and you will need to ask the user to clarify the ambiguity. Only ask one question at a time.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
""".strip()


def max_steps_reached_processor(
    ctx: RunContext[None],
    messages: list[ModelMessage],
    max_steps: int,
) -> list[ModelMessage]:
    assert messages is ctx.messages  # We want the injected message to be preserved in the message history as well
    if ctx.run_step == max_steps:
        content = "You have reached the maximum number of steps. You have one more attempt to execute the `run_query` tool with the final query and then the `finish` tool"
        messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
    return messages


class AmbigFlatSQLAgentConfig(BaseModel):
    llm: str
    schema_formatter: str
    compress_schema: bool = True
    temperature: float = 0.0
    max_steps: int = 20


@agent_registry.register
class AmbigFlatSQLAgent:
    name: ClassVar = "ambig_flat_sql_agent"
    config_cls: ClassVar = AmbigFlatSQLAgentConfig

    def __init__(
        self,
        config: AmbigFlatSQLAgentConfig,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()

    @classmethod
    async def from_config_async(cls, config: AmbigFlatSQLAgentConfig) -> "AmbigFlatSQLAgent":
        return cls(config)

    def _get_agent(
        self,
        system_prompt: str,
        output_type: type[BaseModel],
        tools: list[BaseTool],
    ) -> Agent[None, str]:
        model_settings = {"temperature": self.config.temperature}
        agent = Agent[None, str](
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for tool in tools],
            output_type=output_type,
            instructions=system_prompt,
            history_processors=[partial(max_steps_reached_processor, max_steps=self.config.max_steps)],
            model_settings=model_settings,
        )
        agent.instrument_all()
        return agent

    async def _disambiguate_async(self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector) -> list[str]:
        disamb_agent = self._get_agent(
            system_prompt=jinja2.Template(DISAMBIGUATION_PROMPT).render(language=task.language),
            output_type=list[str],
            tools=[
                GetSchemaTool(
                    (await SchemaCompressor().run_async(db_connector.schema))
                    if self.config.compress_schema
                    else db_connector.schema,
                    self.formatter,
                ),
                GetColumnDescriptionTool(db_connector),
                SearchKeywordsTool(db_connector),
            ],
        )
        result = await disamb_agent.run(task.question)
        return result.output

    async def _generate_sql_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, interpretation: str, idx: int
    ) -> PredQuery:
        all_tools = [
            GetSchemaTool(
                (await SchemaCompressor().run_async(db_connector.schema))
                if self.config.compress_schema
                else db_connector.schema,
                self.formatter,
            ),
            GetColumnDescriptionTool(db_connector),
            SearchKeywordsTool(db_connector),
            RunQueryTool(db_connector),
            FinishTool(),
        ]

        sql_agent = self._get_agent(
            system_prompt=jinja2.Template(TEXT2SQL_PROMPT).render(language=task.language),
            output_type=all_tools[-1].as_pydantic_ai_tool(),
            tools=all_tools[:-1],
        )
        result = await sql_agent.run(f"{task.question} {interpretation}")
        return PredQuery(id=f"PQRY-{idx}", query=extract_code(result.output))

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> FlatAmbigNL2QTaskOutput:
        t0 = time.time()

        interpretations = await self._disambiguate_async(task, db_connector)
        pred_queries = asyncio.gather(
            *[self._generate_sql_async(task, db_connector, s, i) for i, s in enumerate(interpretations)]
        )
        (user_response,) = await user_simulator.ask_async(
            [UserMultipleChoiceQuestion(question=task.question, options=interpretations)]
        )

        messages = result.all_messages()[:-1]
        pred_query = PredQuery(query=extract_code(result.output))
        trajectory = Trajectory.from_pydantic_ai_messages(messages)

        usages = [Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)]
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["api_cost_usd"] = sum(usage.api_cost_usd for usage in usages)
        metrics["input_tokens"] = sum(usage.input_tokens for usage in usages)
        metrics["output_tokens"] = sum(usage.output_tokens for usage in usages)
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {tool.name: tool.get_metrics().model_dump() for tool in all_tools}  # type: ignore

        return FlatAmbigNL2QTaskOutput(
            **task.model_dump(),
            interpretations=interpretations,
            pred_queries=pred_queries,
            pred_intended_query_id=pred_queries[user_response.answer_index].id,
            pred_intended_query=pred_query,
            trajectory=trajectory,
            usages=usages,
            inference_metrics=metrics,
        )
