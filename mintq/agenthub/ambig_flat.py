import asyncio
import json
import jinja2
import time
from typing import ClassVar, Literal, Any
from pydantic import BaseModel
from pydantic_ai import Agent, ToolOutput
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.schema import (
    AmbigNL2QTask,
    FlatAmbigNL2QTaskOutput,
    PredQuery,
    Usage,
    Trajectory,
    PredAmbiguityPointInfinite,
)
from mintq.toolhub import (
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.agenthub.base import (
    agent_registry,
    BaseAgentConfig,
    BaseUserSimulator,
    UserMultipleChoiceQuestion,
    UserValueQuestion,
)
from mintq.agenthub.utils import get_max_steps_processor, instrument, TaskRunContext, BasicAgentConfig
from mintq.metadata_synthesizers import SchemaCompressor
from mintq.utils import int_to_letter


DISAMBIGUATION_PROMPT = """
You are a helpful AI database expert that can disambiguate questions about a {{language}} database.
Given an ambiguous question, you need to output the list of ALL possible interpretations of the question. Try to be comprehensive.
- Each interpretation should be unambiguous.
- Each interpretation should be exclusive - only one can apply at a time.
- Do not resolve threshold-like ambiguities where the number of interpretations is infinite.
- Do not add number index prefixes to the interpretations.

{% if dataset_instructions %}=== START OF DATASET INSTRUCTIONS ===
Do not consider these as ambiguities:
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ==={% endif %}

=== START OF EXAMPLE ===
User: List all interpretations: List all students with high GPA from NY.

Assistant:
<function name="get_schema">
</function>

Tool:
```
=== TABLE: student (50 rows) ===
- id: INTEGER (e.g. 1) [PK]
- name: TEXT (e.g. "John Doe")
- gpa: FLOAT (e.g. 3.5)
- city: TEXT (e.g. "Los Angeles")
- state: TEXT (e.g. "CA")
=== END OF TABLE ===
```

Assistant:
<function name="final_result">
<arg name="interpretations">
- List all students with high GPA from New York City.
- List all students with high GPA from New York State.
</arg>
</function>
=== END OF EXAMPLE ===
""".strip()


DISAMBIGUATE_PARAMETERS_PROMPT = """
You are a helpful AI database expert that can identify ambiguity thresholds in a question about a {{language}} database.
Given a question, you need to identify the threshold-like ambiguous phrases (e.g. "tall", "young", etc.) that correpond to integer, float, or date thresholds.
Each threshold-like ambiguity will become a parameter in the final query and you need to output its relevant information.
The question might or might not contain threshold-like ambiguities. Output an empty list if there are no threshold-like ambiguities.

{% if dataset_instructions %}=== START OF DATASET INSTRUCTIONS ===
Do not consider these as ambiguities:
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ==={% endif %}
""".strip()


TEXT2SQL_PROMPT = """
You are a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions.
- Adhere strictly to the given database schema when constructing queries.
- If you use any of the provided parameters,
  - write a parameterized query with placeholders in the format of `<expr> <operator> :<param_name>`
  - pass in the parameters in the `parameters` field when using the `run_query` tool

{% if dataset_instructions %}=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ==={% endif %}
""".strip()


class AmbigFlatSQLAgentConfig(BasicAgentConfig):
    query_for_intended_only: bool = True


@agent_registry.register
class AmbigFlatSQLAgent:
    name: ClassVar = "ambig_flat_sql_agent"
    task_type: ClassVar = "ambig"
    output_type: ClassVar = "ambig-flat"
    config_cls: ClassVar[type[BaseAgentConfig]] = AmbigFlatSQLAgentConfig

    def __init__(
        self,
        config: AmbigFlatSQLAgentConfig,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()
        self.compressor = SchemaCompressor() if config.compress_schema else None

    @classmethod
    async def from_config_async(cls, config: AmbigFlatSQLAgentConfig) -> "AmbigFlatSQLAgent":
        return cls(config)

    def _get_agent(
        self,
        ctx: TaskRunContext,
        system_prompt: str,
        output_type: type[BaseModel] | ToolOutput[PredQuery],
        tool_keys: list[str],
    ) -> Agent[None, Any]:
        return Agent[None, Any](  # type: ignore
            model=self.config.llm,
            tools=[ctx.tools[t].as_pydantic_ai_tool() for t in tool_keys],
            output_type=output_type,
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )

    async def _disambiguate_interpretations_async(self, ctx: TaskRunContext) -> list[str]:
        class LLMOutput(BaseModel):
            interpretations: list[str]

        disamb_interp_agent: Agent[None, LLMOutput] = self._get_agent(
            ctx,
            system_prompt=jinja2.Template(DISAMBIGUATION_PROMPT).render(
                language=ctx.task.language, dataset_instructions=ctx.task.dataset_instructions
            ),
            output_type=LLMOutput,
            tool_keys=["get_schema"],  # "get_column_description", "search_keywords"
        )
        result = await disamb_interp_agent.run(f"List all interpretations: {ctx.task.question}")
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DISAMB-INTERP"))
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return result.output.interpretations

    async def _disambiguate_parameters_async(self, ctx: TaskRunContext) -> list[PredAmbiguityPointInfinite]:
        class LLMPredAmbiguityPointInfinite(BaseModel):
            phrase: str
            parameter_name: str
            parameter_dtype: Literal["int", "float", "str"]
            parameter_description: str
            parameter_sample_operators: list[Literal["<", ">", "<=", ">=", "=", "<>"]]
            parameter_sample_values: list[int | float | str]

        class LLMOutput(BaseModel):
            parameter_ambiguity_points: list[LLMPredAmbiguityPointInfinite]

        disamb_param_agent: Agent[None, LLMOutput] = self._get_agent(
            ctx,
            system_prompt=jinja2.Template(DISAMBIGUATE_PARAMETERS_PROMPT).render(
                language=ctx.task.language, dataset_instructions=ctx.task.dataset_instructions
            ),
            output_type=LLMOutput,
            tool_keys=["get_schema"],  # "get_column_description", "search_keywords"
        )
        result = await disamb_param_agent.run(f"List all parameter ambiguity points: {ctx.task.question}")
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DISAMB-PARAM"))
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return [
            PredAmbiguityPointInfinite(**ap.model_dump(), id=int_to_letter(i))
            for i, ap in enumerate(result.output.parameter_ambiguity_points)
        ]

    async def _generate_sql_async(
        self,
        ctx: TaskRunContext,
        interpretation: str,
        query_id: str,
        params: list[PredAmbiguityPointInfinite],
    ) -> PredQuery:
        sql_agent: Agent[None, PredQuery] = self._get_agent(
            ctx,
            system_prompt=jinja2.Template(TEXT2SQL_PROMPT).render(
                language=ctx.task.language, dataset_instructions=ctx.task.dataset_instructions
            ),
            output_type=ctx.tools["finish"].as_pydantic_ai_tool(),  # type: ignore
            tool_keys=["get_schema", "get_column_description", "search_keywords", "run_query"],
        )
        params_str = json.dumps(
            [
                {
                    "param_operator": ap.intended_paramter_operator or ap.parameter_sample_operators[0],
                    "param_name": ap.parameter_name,
                    "param_value": ap.intended_parameter_value or ap.parameter_sample_values[0],
                }
                for ap in params
            ],
            indent=2,
            default=str,
        )
        params_str = f"You can use any of the following parameters as placeholders in the query:\n{params_str}"
        result = await sql_agent.run(f"{ctx.task.question} {interpretation}\n{params_str}")
        pred_query = result.output
        pred_query.id = query_id
        ctx.trajectories.append(
            Trajectory.from_pydantic_ai_messages(result.all_messages(), id=f"TRJY-GEN-SQL-{query_id}")
        )
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return pred_query

    async def _resolve_async(
        self,
        question: str,
        interpretations: list[str],
        params: list[PredAmbiguityPointInfinite],
        user_simulator: BaseUserSimulator,
    ) -> int:
        responses = await asyncio.gather(
            *[
                user_simulator.ask_async(
                    UserValueQuestion(
                        question=f'What is {ap.parameter_name} for "{ap.phrase}"? {ap.parameter_description or ""}',
                        value_dtype=ap.parameter_dtype,
                        value_operator_options=ap.parameter_sample_operators,
                    )
                )
                for ap in params
            ]
        )
        for ap, response in zip(params, responses):
            ap.intended_paramter_operator = response.operator
            ap.intended_parameter_value = response.value

        user_response = await user_simulator.ask_async(
            UserMultipleChoiceQuestion(question=question, options=interpretations)
        )
        return user_response.answer_index

    def _fix_pred_queries(self, pred_queries: list[PredQuery], params: list[PredAmbiguityPointInfinite]) -> None:
        """Replace with the intended parameter operator and value in the pred_queries"""
        for ap in params:
            for pred_query in pred_queries:
                if ap.parameter_name in pred_query.parameter_names:
                    original_expr = f"{ap.parameter_sample_operators[0]} :{ap.parameter_name}"
                    pred_query.query = pred_query.query.replace(
                        original_expr, f"{ap.intended_paramter_operator} :{ap.parameter_name}"
                    )
                    pred_query.parameter_values[ap.parameter_name] = ap.intended_parameter_value

    async def _get_tools(self, db_connector: BaseSQLDBConnector) -> dict[str, BaseTool]:
        return {
            "get_schema": GetSchemaTool(db_connector.schema, self.formatter, self.compressor),
            "get_column_description": GetColumnDescriptionTool(db_connector),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }

    @instrument
    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> FlatAmbigNL2QTaskOutput:
        t0 = time.time()

        tools = await self._get_tools(db_connector)
        ctx = TaskRunContext(task, db_connector, Usage.create(llm=self.config.llm), tools)

        interpretations = await self._disambiguate_interpretations_async(ctx)
        parameters = await self._disambiguate_parameters_async(ctx)

        intended_idx = await self._resolve_async(task.question, interpretations, parameters, user_simulator)
        pred_intended_query_id = f"PQRY-{intended_idx}"

        if self.config.query_for_intended_only:
            pred_queries = [
                await self._generate_sql_async(ctx, interpretations[intended_idx], pred_intended_query_id, parameters)
            ]
        else:
            pred_queries = await asyncio.gather(
                *[
                    self._generate_sql_async(ctx, interpretation, f"PQRY-{i}", parameters)
                    for i, interpretation in enumerate(interpretations)
                ]
            )

        self._fix_pred_queries(pred_queries, parameters)

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in ctx.tools.items()}  # type: ignore

        return FlatAmbigNL2QTaskOutput(
            **task.model_dump(),
            interpretations=interpretations,
            parameters=parameters,
            pred_queries=pred_queries,
            pred_intended_query_id=pred_intended_query_id,
            trajectory=ctx.trajectories + [user_simulator.trajectory()],
            usage=ctx.usage,
            user_simulator_usage=user_simulator.usage(),
            inference_metrics=metrics,
        )
