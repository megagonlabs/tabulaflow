import asyncio
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
    PredQuery,
    Usage,
    Trajectory,
    PredAmbiguityPointFinite,
    PredAmbiguityPointInfinite,
    PredAmbiguityPoint,
    StructuredAmbigNL2QTaskOutput,
)
from mintq.toolhub import (
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.agenthub.base import agent_registry, BaseUserSimulator, UserMultipleChoiceQuestion, UserValueQuestion
from mintq.agenthub.utils import get_max_steps_processor, instrument, TaskRunContext, BasicAgentConfig
from mintq.metadata_synthesizers import SchemaCompressor
from mintq.utils import int_to_letter


DISAMBIGUATION_PROMPT = """
You are a helpful AI database expert that can disambiguate questions about a {{language}} database.
Given an ambiguous question, you need to output the list of all ambiguity points in the question.

- For phrases where the number of interpretations is finite, put the list of all possible disambiguated interpretations in the `finite_ambiguity_points` field.
  - There should be at least two interpretations for a phrase to be ambiguous.
  - Do not add number index prefixes to the interpretations.
- For phrases with threshold-like ambiguities (e.g. "tall", "young", etc.), put them in the `parameter_ambiguity_points` field.
=== START OF EXAMPLE ===
Database Schema:
    CREATE TABLE student (
        id: INT,
        name: TEXT,
        gpa: FLOAT,
        city: TEXT,
        state: TEXT,
    );
Question: List all students with high GPA from NY.
Output:
{
  "finite_ambiguity_points": [
    {
      "phrase": "NY",
      "interpretations": [
        "New York City",
        "New York State"
      ]
    }
  ],
  "parameter_ambiguity_points": [
    { 
      "phrase": "high GPA",
      "name": "gpa_threshold",
      "value_dtype": "float",
      "value_operator_options": [">", ">="]
    }
  ]
}
=== END OF EXAMPLE ===
""".strip()


TEXT2SQL_PROMPT = """
You are a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- If you use any of the provided parameters,
  - write a parameterized query with placeholders in the format of `<expr> <operator> :<param_name>`
  - pass in the parameters in the `parameters` field when using the `run_query` tool
""".strip()


@agent_registry.register
class AmbigStructuredSQLAgent:
    name: ClassVar = "ambig_structured_sql_agent"
    task_type: ClassVar = "ambig"
    output_type: ClassVar = "ambig-structured"
    config_cls: ClassVar = BasicAgentConfig

    def __init__(
        self,
        config: BasicAgentConfig,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "AmbigStructuredSQLAgent":
        return cls(config)

    def _get_agent(
        self,
        ctx: TaskRunContext,
        system_prompt: str,
        output_type: type[BaseModel],
        tool_keys: list[str],
    ) -> Agent[None, str]:
        return Agent[None, str](
            model=self.config.llm,
            tools=[ctx.tools[t].as_pydantic_ai_tool() for t in tool_keys],
            output_type=output_type,
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings={"temperature": self.config.temperature},
        )

    async def _disambiguate_async(self, ctx: TaskRunContext) -> list[PredAmbiguityPoint]:
        class LLMPredAmbiguityPointFinite(BaseModel):
            phrase: str
            interpretations: list[str]

        class LLMPredAmbiguityPointInfinite(BaseModel):
            phrase: str
            parameter_name: str
            parameter_dtype: Literal["int", "float", "str"]
            parameter_description: str
            parameter_sample_operators: list[Literal["<", ">", "<=", ">=", "=", "<>"]]
            parameter_sample_values: list[int | float | str]

        class LLMOutput(BaseModel):
            finite_ambiguity_points: list[LLMPredAmbiguityPointFinite]
            parameter_ambiguity_points: list[LLMPredAmbiguityPointInfinite]

        disamb_agent = self._get_agent(
            ctx,
            system_prompt=jinja2.Template(DISAMBIGUATION_PROMPT).render(language=ctx.task.language),
            output_type=LLMOutput,
            tool_keys=["get_schema"],  # "get_column_description"
        )
        result = await disamb_agent.run(f"List all ambiguity points: {ctx.task.question}")
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DISAMB"))
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)

        res = []
        for ap in result.output.finite_ambiguity_points:
            res.append(PredAmbiguityPointFinite(**ap.model_dump(), id=int_to_letter(len(res))))
        for ap in result.output.parameter_ambiguity_points:
            res.append(PredAmbiguityPointInfinite(**ap.model_dump(), id=int_to_letter(len(res))))
        return res

    async def _generate_sql_async(
        self,
        ctx: TaskRunContext,
        finite_aps: list[PredAmbiguityPointFinite],
        finite_interpretation_indexes: list[int],
        infinite_aps: list[PredAmbiguityPointInfinite],
    ) -> PredQuery:
        assert len(finite_aps) == len(finite_interpretation_indexes)

        sql_agent = self._get_agent(
            ctx,
            system_prompt=jinja2.Template(TEXT2SQL_PROMPT).render(language=ctx.task.language),
            output_type=ctx.tools["finish"].as_pydantic_ai_tool(),
            tool_keys=["get_schema", "get_column_description", "search_keywords", "run_query"],
        )
        prompt = ctx.task.question
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
        prompt += f"\nYou can use any of the following parameters as placeholders in the query:\n{json.dumps(params, indent=2, default=str)}"
        result = await sql_agent.run(prompt)
        query_id = "PQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, finite_interpretation_indexes))
        pred_query: PredQuery = result.output
        pred_query.id = query_id
        ctx.trajectories.append(
            Trajectory.from_pydantic_ai_messages(result.all_messages(), id=f"TRJY-GEN-SQL-{query_id}")
        )
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
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

                for pred_query in pred_queries:
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
    async def predict_no_user_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector
    ) -> StructuredAmbigNL2QTaskOutput:
        t0 = time.time()

        tools = {
            "get_schema": GetSchemaTool(
                (await SchemaCompressor().run_async(db_connector.schema))
                if self.config.compress_schema
                else db_connector.schema,
                self.formatter,
            ),
            "get_column_description": GetColumnDescriptionTool(db_connector),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }

        ctx = TaskRunContext(task, db_connector, Usage.create(llm=self.config.llm), tools)

        ambiguity_points = await self._disambiguate_async(ctx)

        finite_aps = [ap for ap in ambiguity_points if ap.type == "finite"]
        all_indexes = list(itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps]))
        infinite_aps = [ap for ap in ambiguity_points if ap.type == "infinite"]

        pred_queries = await asyncio.gather(
            *[self._generate_sql_async(ctx, finite_aps, indexes, infinite_aps) for indexes in all_indexes]
        )
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in ctx.tools.items()}  # type: ignore

        return StructuredAmbigNL2QTaskOutput(
            **task.model_dump(),
            pred_ambiguity_points=ambiguity_points,
            pred_queries=pred_queries,
            pred_intended_query_id=None,
            trajectory=ctx.trajectories,
            usage=ctx.usage,
            user_simulator_usage=None,
            inference_metrics=metrics,
        )

    @instrument
    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> StructuredAmbigNL2QTaskOutput:
        t0 = time.time()

        task_output = await self.predict_no_user_async(task, db_connector)

        pred_intended_query_id = await self._resolve_async(
            task_output.pred_ambiguity_points, task_output.pred_queries, user_simulator
        )
        task_output.pred_intended_query_id = pred_intended_query_id
        task_output.trajectory.append(user_simulator.trajectory())
        task_output.inference_metrics["latency_seconds"] = time.time() - t0
        task_output.user_simulator_usage = user_simulator.usage()
        return StructuredAmbigNL2QTaskOutput.model_validate(task_output.model_dump())
