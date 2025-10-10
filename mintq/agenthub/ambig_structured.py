import asyncio
import datetime
import json
import jinja2
import time
import itertools
from typing import ClassVar, Literal
from pydantic import BaseModel
from pydantic_ai import Agent
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.schema import (
    AmbigNL2QTask,
    FlatAmbigNL2QTaskOutput,
    PredQuery,
    Usage,
    Trajectory,
    PredAmbiguityPointFinite,
    PredAmbiguityPointInfinite,
    PredAmbiguityPoint,
    StructuredAmbigNL2QTaskOutput,
)
from mintq.toolhub import (
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.agenthub.base import agent_registry, BaseUserSimulator, UserMultipleChoiceQuestion, UserValueQuestion
from mintq.agenthub.utils import get_max_steps_processor, instrument
from mintq.metadata_synthesizers import SchemaCompressor


DISAMBIGUATION_PROMPT = """
You are a helpful AI database expert that can disambiguate questions about a {{language}} database.
Given an ambiguous question, you need to output the list of all ambiguity points in the question.

=== START OF EXAMPLE ===
Database Schema:
    CREATE TABLE student (
        id: INT,
        name: TEXT,
        gpa: FLOAT,
        city: TEXT,
        state: TEXT,
    );
Question: List all students with from NY.
Ambiguity Points:
[
{
    "phrase": "high GPA",
    "name": "gpa_threshold",
    "value_dtype": "float",
    "value_operator_options": [">", ">="],
},
{
    "phrase": "NY",
    "interpretations": [
        "New York City",
        "New York State",
    ]
}
=== END OF EXAMPLE ===
""".strip()


TEXT2SQL_PROMPT = """
You are a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- The question is ambiguous and you will need to ask the user to clarify the ambiguity. Only ask one question at a time.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- If you use any of the provided parameters,
  - write a parameterized query with placeholders in the format of `<expr> <operator> :<param_name>`
  - pass in the parameters in the `parameters` field when using the `run_query` tool
""".strip()


class AmbigStructuredSQLAgentConfig(BaseModel):
    llm: str
    schema_formatter: str
    compress_schema: bool = True
    temperature: float = 0.0
    max_steps: int = 20


AMBIGUITY_POINT_IDS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@agent_registry.register
class AmbigStructuredSQLAgent:
    name: ClassVar = "ambig_structured_sql_agent"
    config_cls: ClassVar = AmbigStructuredSQLAgentConfig

    def __init__(
        self,
        config: AmbigStructuredSQLAgentConfig,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()

        self._tools = []
        self._trajectories = []
        self._usage = Usage.create(llm=config.llm)

    @classmethod
    async def from_config_async(cls, config: AmbigStructuredSQLAgentConfig) -> "AmbigStructuredSQLAgent":
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
        return agent

    async def _disambiguate_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector
    ) -> list[PredAmbiguityPoint]:
        class LLMPredAmbiguityPointFinite(BaseModel):
            phrase: str
            interpretations: list[str]

        class LLMPredAmbiguityPointInfinite(BaseModel):
            phrase: str
            parameter_name: str
            parameter_dtype: Literal["int", "float", "date"]
            parameter_description: str
            parameter_sample_operators: list[Literal["<", ">", "<=", ">="]]
            parameter_sample_values: list[int | float | datetime.date]

        class LLMOutput(BaseModel):
            ambiguity_points: list[LLMPredAmbiguityPointFinite | LLMPredAmbiguityPointInfinite]

        disamb_interp_agent = self._get_agent(
            system_prompt=jinja2.Template(DISAMBIGUATION_PROMPT).render(language=task.language),
            output_type=LLMOutput,
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
        result = await disamb_interp_agent.run(f"List all ambiguity points: {task.question}")
        self._trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DISAMB"))
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)

        res = []
        for i, ap in enumerate(result.output.ambiguity_points):
            if isinstance(ap, LLMPredAmbiguityPointFinite):
                res.append(PredAmbiguityPointFinite(**ap.model_dump(), id=AMBIGUITY_POINT_IDS[i]))
            elif isinstance(ap, LLMPredAmbiguityPointInfinite):
                res.append(PredAmbiguityPointInfinite(**ap.model_dump(), id=AMBIGUITY_POINT_IDS[i]))
        return res

    async def _generate_sql_async(
        self,
        task: AmbigNL2QTask,
        db_connector: BaseSQLDBConnector,
        finite_aps: list[PredAmbiguityPointFinite],
        finite_interpretation_indexes: list[int],
        infinite_aps: list[PredAmbiguityPointInfinite],
    ) -> PredQuery:
        assert len(finite_aps) == len(finite_interpretation_indexes)
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
        prompt = task.question
        for ap, idx in zip(finite_aps, finite_interpretation_indexes):
            prompt += f"\n- {ap.phrase}: {ap.interpretations[idx]}"
        params = [
            {
                "param_operator": ap.parameter_sample_operators[0],
                "param_name": ap.parameter_name,
                "param_value": ap.parameter_sample_values[0],
            }
            for ap in infinite_aps
        ]
        prompt += f"\nYou can use any of the following parameters as placeholders in the query:\n{json.dumps(params, indent=2)}"
        result = await sql_agent.run(prompt)
        query_id = "PQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, finite_interpretation_indexes))
        pred_query: PredQuery = result.output
        pred_query.id = query_id
        self._trajectories.append(
            Trajectory.from_pydantic_ai_messages(result.all_messages(), id=f"TRJY-GEN-SQL-{query_id}")
        )
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return pred_query

    async def _resolve_async(
        self,
        ambiguity_points: list[PredAmbiguityPoint],
        pred_queries: list[PredQuery],
        user_simulator: BaseUserSimulator,
    ) -> str:
        for ap in ambiguity_points:
            if ap.type == "finite":
                response = await user_simulator.ask_async(
                    UserMultipleChoiceQuestion(question=ap.phrase, options=ap.interpretations)
                )
                ap.intended_interpretation_idx = response.answer_index
            elif ap.type == "infinite":
                response = await user_simulator.ask_async(
                    UserValueQuestion(
                        question=f"{ap.phrase}: {ap.parameter_description}",
                        value_dtype=ap.parameter_dtype,
                        value_operator_options=ap.parameter_sample_operators,
                    )
                )
                ap.intended_paramter_operator = response.operator
                ap.intended_parameter_value = response.value

        # Fix the operator in the queries
        infinite_aps = [ap for ap in ambiguity_points if ap.type == "infinite"]
        for pred_query in pred_queries:
            for ap in infinite_aps:
                if ap.parameter_name in pred_query.parameter_names:
                    original_expr = f"{ap.parameter_sample_operators[0]} :{ap.parameter_name}"
                    pred_query.query = pred_query.query.replace(
                        original_expr, f"{ap.intended_paramter_operator} :{ap.parameter_name}"
                    )

        pred_intended_query_id = "PQRY" + "".join(
            f"-{ap.id}.{ap.intended_interpretation_idx}" for ap in ambiguity_points if ap.type == "finite"
        )
        return pred_intended_query_id

    @instrument
    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> FlatAmbigNL2QTaskOutput:
        t0 = time.time()

        ambiguity_points = await self._disambiguate_async(task, db_connector)

        finite_aps = [ap for ap in ambiguity_points if ap.type == "finite"]
        all_indexes = list(itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps]))
        infinite_aps = [ap for ap in ambiguity_points if ap.type == "infinite"]

        pred_queries = await asyncio.gather(
            *[
                self._generate_sql_async(task, db_connector, finite_aps, indexes, infinite_aps)
                for indexes in all_indexes
            ]
        )

        pred_intended_query_id = await self._resolve_async(ambiguity_points, pred_queries, user_simulator)

        self._trajectories.append(user_simulator.trajectory())
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["tools"] = {tool.name: tool.get_metrics().model_dump() for tool in self._tools}  # type: ignore

        return StructuredAmbigNL2QTaskOutput(
            **task.model_dump(),
            pred_ambiguity_points=ambiguity_points,
            pred_queries=pred_queries,
            pred_intended_query_id=pred_intended_query_id,
            trajectory=self._trajectories,
            usage=self._usage,
            user_simulator_usage=user_simulator.usage(),
            inference_metrics=metrics,
        )
