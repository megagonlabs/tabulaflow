import asyncio
import datetime
import json
import jinja2
import time
from typing import ClassVar, Literal
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.schema import AmbigNL2QTask, FlatAmbigNL2QTaskOutput, PredQuery, Usage, Trajectory
from mintq.toolhub import (
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.agenthub.base import agent_registry, BaseUserSimulator, UserMultipleChoiceQuestion, UserValueQuestion
from mintq.agenthub.utils import get_max_steps_processor
from mintq.metadata_synthesizers import SchemaCompressor


DISAMBIGUATION_PROMPT = """
You are a helpful AI database expert that can disambiguate questions about a {{language}} database.
Given an ambiguous question, you need to output the list of all possible interpretations of the question.
Do not resolve threshold-like ambiguities where the number of interpretations is infinite.
Do not add number index prefixes to the interpretations.

=== START OF EXAMPLE ===
Database Schema:
    CREATE TABLE student (
        id: INT,
        name: TEXT,
        gpa: FLOAT,
        city: TEXT,
        state: TEXT,
    );
Question: List all students from NY.
Interpretations:
- List all students from New York City.
- List all students from New York State.
=== END OF EXAMPLE ===
""".strip()


DISAMBIGUATE_PARAMETERS_PROMPT = """
You are a helpful AI database expert that can identify ambiguity thresholds in a question about a {{language}} database.
Given a question, you need to identify the threshold-like ambiguous phrases (e.g. "tall", "young", etc.) that correpond to integer, float, or date thresholds.
Each threshold-like ambiguity will become a parameter in the final query and you need to output its relevant information.
The question might or might not contain threshold-like ambiguities. Output an empty list if there are no threshold-like ambiguities.
""".strip()


TEXT2SQL_PROMPT = """
You are a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- The question is ambiguous and you will need to ask the user to clarify the ambiguity. Only ask one question at a time.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- If you use any of the provided parameters, you must write a parameterized query with placeholders and pass in the parameters in the `parameters` field when using the `run_query` tool.
""".strip()


class AmbigFlatSQLAgentConfig(BaseModel):
    llm: str
    schema_formatter: str
    compress_schema: bool = True
    temperature: float = 0.0
    max_steps: int = 20


class ParameterAmbiguityPoint(BaseModel):
    phrase: str = Field(description="The phrase in the questionthat is ambiguous.")
    name: str = Field(description="The variable name of the parameter that can be used in the query.")
    explanation: str = Field(description="A short explanation of why this parameter is ambiguous.")
    value_dtype: Literal["int", "float", "date"] = Field(description="The data type of the parameter value.")
    value_operator_options: list[Literal["<", ">", "<=", ">="]] = Field(
        default_factory=list,
        description="List of applicable operators that can be used in `WHERE <column> <operator> <parameter_name>`.",
    )


class ResolvedParameterAmbiguityPoint(ParameterAmbiguityPoint):
    value_operator: Literal["<", ">", "<=", ">="]
    value: int | float | datetime.date


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
        self._disamb_interpretations_result = None
        self._disamb_parameters_result = None
        self._generate_sql_results = []
        self._tools = []
        self._trajectories = []
        self._usage = Usage.create(llm=config.llm)

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
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=model_settings,
        )
        agent.instrument_all()
        return agent

    async def _disambiguate_interpretations_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector
    ) -> list[str]:
        class Output(BaseModel):
            interpretations: list[str]

        disamb_agent = self._get_agent(
            system_prompt=jinja2.Template(DISAMBIGUATION_PROMPT).render(language=task.language),
            output_type=Output,
            tools=[
                GetSchemaTool(
                    (await SchemaCompressor().run_async(db_connector.schema))
                    if self.config.compress_schema
                    else db_connector.schema,
                    self.formatter,
                ),
                # GetColumnDescriptionTool(db_connector),
                # SearchKeywordsTool(db_connector),
            ],
        )
        result = await disamb_agent.run(f"List all interpretations: {task.question}")
        self._disamb_interpretations_result = result
        self._trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DISAMB-INTERP"))
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return result.output.interpretations

    async def _disambiguate_parameters_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector
    ) -> list[ParameterAmbiguityPoint]:
        disamb_agent = self._get_agent(
            system_prompt=jinja2.Template(DISAMBIGUATE_PARAMETERS_PROMPT).render(language=task.language),
            output_type=list[ParameterAmbiguityPoint],
            tools=[
                GetSchemaTool(
                    (await SchemaCompressor().run_async(db_connector.schema))
                    if self.config.compress_schema
                    else db_connector.schema,
                    self.formatter,
                ),
                # GetColumnDescriptionTool(db_connector),
                # SearchKeywordsTool(db_connector),
            ],
        )
        result = await disamb_agent.run(task.question)
        self._disamb_parameters_result = result
        self._trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DISAMB-PARAMS"))
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return result.output

    async def _generate_sql_async(
        self,
        task: AmbigNL2QTask,
        db_connector: BaseSQLDBConnector,
        interpretation: str,
        query_id: str,
        resolved_params: list[ResolvedParameterAmbiguityPoint],
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
        self._tools += all_tools

        sql_agent = self._get_agent(
            system_prompt=jinja2.Template(TEXT2SQL_PROMPT).render(language=task.language),
            output_type=all_tools[-1].as_pydantic_ai_tool(),
            tools=all_tools[:-1],
        )
        params = [{"param_operator": p.value_operator, "param_name": p.name} for p in resolved_params]
        params = f"You can use any of the following parameters as placeholders in the query: {json.dumps(params)}"
        result = await sql_agent.run(f"{task.question} {interpretation}\n{params}")
        self._generate_sql_results.append(result)
        pred_query: PredQuery = result.output
        pred_query.id = query_id
        self._trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id=f"TRJY-GEN-SQL-{query_id}"))
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return pred_query

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> FlatAmbigNL2QTaskOutput:
        t0 = time.time()

        interpretations = await self._disambiguate_interpretations_async(task, db_connector)
        params = await self._disambiguate_parameters_async(task, db_connector)

        if params:
            questions = [
                UserValueQuestion(
                    question=f"{ap.phrase}: {ap.explanation}",
                    value_dtype=ap.value_dtype,
                    value_operator_options=ap.value_operator_options,
                )
                for ap in params
            ]
            responses = [(await user_simulator.ask_async(question)) for question in questions]
            resolved_params = [
                ResolvedParameterAmbiguityPoint(
                    **ap.model_dump(), value_operator=response.operator, value=response.value
                )
                for ap, response in zip(params, responses)
            ]
        else:
            resolved_params = []

        pred_queries = await asyncio.gather(
            *[
                self._generate_sql_async(task, db_connector, s, f"PQRY-{i}", resolved_params)
                for i, s in enumerate(interpretations)
            ]
        )
        user_response = await user_simulator.ask_async(
            UserMultipleChoiceQuestion(question=task.question, options=interpretations)
        )

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["tools"] = {tool.name: tool.get_metrics().model_dump() for tool in self._tools}  # type: ignore

        return FlatAmbigNL2QTaskOutput(
            **task.model_dump(),
            interpretations=interpretations,
            pred_queries=pred_queries,
            pred_intended_query_id=pred_queries[user_response.answer_index].id,
            trajectory=self._trajectories,
            usage=self._usage,
            user_simulator_usage=user_simulator.usage(),
            inference_metrics=metrics,
        )
