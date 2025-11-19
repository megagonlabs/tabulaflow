import asyncio
import json
import jinja2
import time
import itertools
from typing import ClassVar, Literal, Any
from pydantic import BaseModel, TypeAdapter
from pydantic_ai import Agent, ToolOutput
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
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.agenthub.base import (
    agent_registry,
    BaseUserSimulator,
    UserMultipleChoiceQuestion,
    UserValueQuestion,
    BaseAgentConfig,
)
from mintq.agenthub.utils import get_max_steps_processor, instrument, TaskRunContext, BasicAgentConfig
from mintq.metadata_synthesizers import SchemaCompressor
from mintq.utils import int_to_letter


DISAMBIGUATION_PROMPT = """
You are a helpful AI database expert that can disambiguate questions about a {{language}} database.
The question has one or multiple ambiguity points and you will need to output the list of ALL ambiguity points in the question. Try to be comprehensive.

- For phrases where the number of interpretations is finite, put the list of all possible disambiguated interpretations in the `finite_ambiguity_points` field.
  - There should be at least two interpretations for a phrase to be ambiguous.
  - Each interpretation should be unambiguous.
  - Each interpretation should be exclusive - only one can apply at a time.
  - If there are multiple dimensions of ambiguity for a phrase, split them into multiple ambiguity points. You can have multiple ambiguity points for one phrase.
  - Do not add number index prefixes to the interpretations.
- For phrases with threshold-like ambiguities (e.g. "tall", "young", etc.), put them in the `parameter_ambiguity_points` field.
  - parameter_sample_operators is a list of valid operators that can be used in <expr> <operator> :<parameter_name>.
  - parameter_sample_values is a list of sample values ordered from least strict to most strict

{% if dataset_instructions %}=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ==={% endif %}

=== START OF EXAMPLE ===
User: List all ambiguity points: List all students with high GPA from NY.

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
<arg name="finite_ambiguity_points">
[
  {
    "phrase": "NY",
    "interpretations": [
      "New York City",
      "New York State"
    ]
  }
]
</arg>
<arg name="parameter_ambiguity_points">
[
  { 
    "phrase": "high GPA",
    "parameter_name": "gpa_threshold",
    "parameter_dtype": "float",
    "parameter_description": "GPA threshold to be considered high",
    "parameter_sample_operators": [">", ">="],
    "parameter_sample_values": [3.5, 4.0]
  }
]
</arg>
</function>
=== END OF EXAMPLE ===
""".strip()


TEXT2SQL_PROMPT = """
You are a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information.
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


class AmbigStructuredSQLAgentConfig(BasicAgentConfig):
    query_for_intended_only: bool = True
    use_gold_phrases: bool = False
    use_gold_ambiguity_points: bool = False


@agent_registry.register
class AmbigStructuredSQLAgent:
    name: ClassVar = "ambig_structured_sql_agent"
    task_type: ClassVar = "ambig"
    output_type: ClassVar = "ambig-structured"
    config_cls: ClassVar[type[BaseAgentConfig]] = AmbigStructuredSQLAgentConfig

    def __init__(
        self,
        config: AmbigStructuredSQLAgentConfig,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()
        self.compressor = SchemaCompressor() if config.compress_schema else None

    @classmethod
    async def from_config_async(cls, config: AmbigStructuredSQLAgentConfig) -> "AmbigStructuredSQLAgent":
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

        disamb_agent: Agent[None, LLMOutput] = self._get_agent(
            ctx,
            system_prompt=jinja2.Template(DISAMBIGUATION_PROMPT).render(
                language=ctx.task.language, dataset_instructions=ctx.task.dataset_instructions
            ),
            output_type=LLMOutput,
            tool_keys=["get_schema"],
        )
        prompt = f"List all ambiguity points: {ctx.task.question}"

        if self.config.use_gold_phrases:
            prompt += (
                "\nFor each phrase listed below, and in the given order, output a single ambiguity point."
                " If a phrase appears more than once, each occurrence represents a distinct dimension of ambiguity."
            )
            for ap in ctx.task.gold_ambiguity_points:  # type: ignore
                if ap.type == "finite":
                    prompt += f'\n- "{ap.phrase}" (finite)'
            for ap in ctx.task.gold_ambiguity_points:  # type: ignore
                if ap.type == "infinite":
                    prompt += f'\n- "{ap.phrase}" (parameter)'

        result = await disamb_agent.run(prompt)
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-DISAMB"))
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)

        res: list[PredAmbiguityPoint] = []
        for ap in result.output.finite_ambiguity_points:
            res.append(PredAmbiguityPointFinite(**ap.model_dump(), id=int_to_letter(len(res))))
        for ap in result.output.parameter_ambiguity_points:
            res.append(PredAmbiguityPointInfinite(**ap.model_dump(), id=int_to_letter(len(res))))
        return res

    async def _generate_sql_async(
        self,
        ctx: TaskRunContext,
        finite_aps: list[PredAmbiguityPointFinite],
        finite_interpretation_indexes: tuple[int, ...],
        infinite_aps: list[PredAmbiguityPointInfinite],
    ) -> PredQuery:
        assert len(finite_aps) == len(finite_interpretation_indexes)

        sql_agent: Agent[None, PredQuery] = self._get_agent(
            ctx,
            system_prompt=jinja2.Template(TEXT2SQL_PROMPT).render(
                language=ctx.task.language, dataset_instructions=ctx.task.dataset_instructions
            ),
            output_type=ctx.tools["finish"].as_pydantic_ai_tool(),  # type: ignore
            tool_keys=["get_schema", "get_column_description", "search_keywords", "run_query"],
        )
        prompt = ctx.task.question
        for ap, idx in zip(finite_aps, finite_interpretation_indexes):
            prompt += f'\n- "{ap.phrase}" means "{ap.interpretations[idx]}"'
        if infinite_aps:
            params = [
                {
                    "param_operator": ap.intended_paramter_operator or ap.parameter_sample_operators[0],
                    "param_name": ap.parameter_name,
                    "param_value": ap.intended_parameter_value or ap.parameter_sample_values[0],
                }
                for ap in infinite_aps
            ]
            prompt += f"\nYou can use any of the following parameters as placeholders in the query:\n{json.dumps(params, indent=2, default=str)}"
        result = await sql_agent.run(prompt)
        query_id = "PQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, finite_interpretation_indexes))
        pred_query = result.output
        pred_query.id = query_id
        ctx.trajectories.append(
            Trajectory.from_pydantic_ai_messages(result.all_messages(), id=f"TRJY-GEN-SQL-{query_id}")
        )
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        return pred_query

    def _fix_pred_queries(self, pred_queries: list[PredQuery], ambiguity_points: list[PredAmbiguityPoint]) -> None:
        """Replace with the intended parameter operator and value in the pred_queries"""
        for ap in ambiguity_points:
            if ap.type == "infinite":
                for pred_query in pred_queries:
                    if ap.parameter_name in pred_query.parameter_names:
                        original_expr = f"{ap.parameter_sample_operators[0]} :{ap.parameter_name}"
                        pred_query.query = pred_query.query.replace(
                            original_expr, f"{ap.intended_paramter_operator} :{ap.parameter_name}"
                        )
                        pred_query.parameter_values[ap.parameter_name] = ap.intended_parameter_value

    async def _resolve_async(
        self,
        ambiguity_points: list[PredAmbiguityPoint],
        user_simulator: BaseUserSimulator,
    ) -> str:
        questions = []
        for ap in ambiguity_points:
            if ap.type == "finite":
                questions.append(
                    UserMultipleChoiceQuestion(question=f'"{ap.phrase}" means', options=ap.interpretations)
                )
            elif ap.type == "infinite":
                questions.append(
                    UserValueQuestion(  # type: ignore
                        question=f'What is {ap.parameter_name} for "{ap.phrase}"? {ap.parameter_description or ""}',
                        value_dtype=ap.parameter_dtype,
                        value_operator_options=ap.parameter_sample_operators,
                    )
                )
        responses = await asyncio.gather(*[user_simulator.ask_async(question) for question in questions])
        for ap, response in zip(ambiguity_points, responses):
            if response is None:
                ap.rejected_by_user = True
            elif ap.type == "finite":
                ap.intended_interpretation_idx = response.answer_index
            elif ap.type == "infinite":
                ap.intended_paramter_operator = response.operator  # type: ignore
                ap.intended_parameter_value = response.value  # type: ignore

        ambiguity_points_resolved = [ap for ap in ambiguity_points if not ap.rejected_by_user]
        pred_intended_query_id = "PQRY" + "".join(
            f"-{ap.id}.{ap.intended_interpretation_idx}" for ap in ambiguity_points_resolved if ap.type == "finite"
        )
        return pred_intended_query_id

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
    ) -> StructuredAmbigNL2QTaskOutput:
        t0 = time.time()

        tools = await self._get_tools(db_connector)

        ctx = TaskRunContext(task, db_connector, Usage.create(llm=self.config.llm), tools)

        if self.config.use_gold_ambiguity_points:
            ambiguity_points = [
                TypeAdapter(PredAmbiguityPoint).validate_python(ap.model_dump()) for ap in task.gold_ambiguity_points
            ]
            assert task.gold_intended_query_id is not None
            pred_intended_query_id = task.gold_intended_query_id.replace("GQRY", "PQRY")
        else:
            ambiguity_points = await self._disambiguate_async(ctx)
            pred_intended_query_id = await self._resolve_async(ambiguity_points, user_simulator)

        finite_aps = [ap for ap in ambiguity_points if ap.type == "finite" and not ap.rejected_by_user]
        infinite_aps = [ap for ap in ambiguity_points if ap.type == "infinite" and not ap.rejected_by_user]

        if self.config.query_for_intended_only:
            indexes = [ap.intended_interpretation_idx for ap in finite_aps]
            pred_queries = [await self._generate_sql_async(ctx, finite_aps, indexes, infinite_aps)]  # type: ignore
        else:
            all_indexes = list(itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps]))
            pred_queries = await asyncio.gather(
                *[self._generate_sql_async(ctx, finite_aps, indexes, infinite_aps) for indexes in all_indexes]
            )

        self._fix_pred_queries(pred_queries, finite_aps + infinite_aps)

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in ctx.tools.items()}  # type: ignore
        metrics["user_effort"] = user_simulator.user_effort()

        return StructuredAmbigNL2QTaskOutput(
            **task.model_dump(),
            pred_ambiguity_points=ambiguity_points,
            pred_queries=pred_queries,
            pred_intended_query_id=pred_intended_query_id,
            trajectory=ctx.trajectories + [user_simulator.trajectory()],
            usage=ctx.usage,
            user_simulator_usage=user_simulator.usage(),
            inference_metrics=metrics,
        )
