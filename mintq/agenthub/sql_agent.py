import asyncio
import copy
import json
import jinja2
import time
from typing import ClassVar
from pydantic import BaseModel
from pydantic_ai import Agent
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import (
    ExtraPredInfo,
    SQLSchema,
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
    PredQuery,
    Usage,
    Trajectory,
    ColumnRef,
)
from mintq.metadata_synthesizers import SchemaCompressor
from mintq.toolhub import (
    BaseTool,
    RunQueryNoParamsTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import (
    get_max_steps_processor,
    instrument,
    BasicAgentConfig,
    TaskRunContext,
)
from mintq.utils import extract_code, extract_all_source_columns

SQL_AGENT_SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information.
- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Follow the dataset and question instructions if they are provided. When there is a conflict between instructions, prioritize the question instructions.
{%- if language == "snowflake" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{%- endif %}
{%- if dataset_instructions %}

=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ===
{%- endif %}
""".strip()


EXPAND_COLUMNS_PROMPT = """
You are a helpful AI database expert.
Given a list of columns that can be used to answer a question, identify potential alternative columns for each of the given columns.

- All table and column names must exactly match those in the database schema.
- The alternative columns can be from the same table or different tables.
- The alternative columns can be an empty list if there are no alternatives.

=== START OF EXAMPLE ===
Question: "What is the date of order 1005?"
Columns: [{table_name: "order", column_name: "order_date"}]
Output:
[
  {
    "original_column": {
      "table_name": "order",
      "column_name": "order_date"
    },
    "alternatives": [
      {
        "table_name": "order",
        "column_name": "shipping_date"
      }
    ]
  }
]
=== END OF EXAMPLE ===

=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===

=== START OF QUESTION ===
{{question}}
{%- if dataset_instructions %}

Additional instructions:
{{dataset_instructions}}
{%- endif %}
=== END OF QUESTION ===

=== START OF COLUMNS ===
{{columns}}
=== END OF COLUMNS ===

Your output:
""".strip()


class SchemaLinker:
    def __init__(self, config: BasicAgentConfig):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()
        self.compressor = SchemaCompressor() if config.compress_schema else None

    async def _generate_sql_async(self, ctx: TaskRunContext) -> PredQuery:
        db_connector = ctx.db_connector
        task = ctx.task

        tools: dict[str, BaseTool] = {
            "get_schema": GetSchemaTool(db_connector.schema, self.formatter, self.compressor),
            "get_column_description": GetColumnDescriptionTool(db_connector),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryNoParamsTool(db_connector),
            "finish": FinishTool(),
        }
        system_prompt = jinja2.Template(SQL_AGENT_SYSTEM_PROMPT).render(
            language=task.language, dataset_instructions=task.dataset_instructions
        )

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(
            f"{task.question}\n{task.question_instructions}" if task.question_instructions else task.question
        )
        pred_query: PredQuery = tools["run_query"].last_pred_query()  # type: ignore
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-SCHEMA-LINK-SQL")
        ctx.trajectories.append(trajectory)
        return pred_query

    async def expand_schema_async(self, ctx: TaskRunContext, schema: SQLSchema, batch_size: int = 5) -> SQLSchema:
        class ColumnWithAlternatives(BaseModel):
            original_column: ColumnRef
            alternatives: list[ColumnRef]

        class LLMOutput(BaseModel):
            results: list[ColumnWithAlternatives]

        current_columns = schema.get_all_column_refs()

        async def process_batch_async(batch_idx: int, batch: list[ColumnRef]) -> list[ColumnWithAlternatives]:
            agent = Agent[None, LLMOutput](  # type: ignore
                model=self.config.llm,
                output_type=LLMOutput,
                model_settings=self.config.to_model_settings(),
            )
            prompt = jinja2.Template(EXPAND_COLUMNS_PROMPT).render(
                schema=self.formatter.format(
                    (await self.compressor.run_async(ctx.db_connector.schema))
                    if self.compressor
                    else ctx.db_connector.schema
                ),
                question=ctx.task.question
                + (f"\n{ctx.task.question_instructions}" if ctx.task.question_instructions else ""),
                dataset_instructions=ctx.task.dataset_instructions,
                columns=json.dumps(
                    [{"table_name": c.table_name, "column_name": c.column_name} for c in batch], indent=2
                ),
            )
            result = await agent.run(prompt)
            ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
            ctx.trajectories.append(
                Trajectory.from_pydantic_ai_messages(result.all_messages(), id=f"TRJY-EXPAND-SCHEMA-{batch_idx}")
            )
            return result.output.results

        batches = [current_columns[i : i + batch_size] for i in range(0, len(current_columns), batch_size)]
        all_results = await asyncio.gather(*[process_batch_async(i, batch) for i, batch in enumerate(batches)])

        linked = set((c.table_name.lower(), c.column_name.lower()) for c in current_columns)
        for results in all_results:
            for item in results:
                for alternative in item.alternatives:
                    linked.add((alternative.table_name.lower(), alternative.column_name.lower()))

        # We keep all foreign key columns so that tables in the linked schema can be joined.
        for col in ctx.db_connector.schema.get_fk_column_refs():
            linked.add((col.table_name.lower(), col.column_name.lower()))

        linked_schema = copy.deepcopy(ctx.db_connector.schema)
        for table in linked_schema.tables:
            table.columns = [col for col in table.columns if (table.name.lower(), col.name.lower()) in linked]
        linked_schema.tables = [table for table in linked_schema.tables if table.columns]
        return linked_schema

    async def link_schema_async(self, ctx: TaskRunContext) -> SQLSchema:
        pred_query = await self._generate_sql_async(ctx)
        # pred_query = ctx.task.gold_query

        source_columns = extract_all_source_columns(pred_query.query, ctx.db_connector.schema)
        source_columns = set((c[0].lower(), c[1].lower()) for c in source_columns)

        linked_schema = copy.deepcopy(ctx.db_connector.schema)
        for table in linked_schema.tables:
            table.columns = [col for col in table.columns if (table.name.lower(), col.name.lower()) in source_columns]
        linked_schema.tables = [table for table in linked_schema.tables if table.columns]

        if not linked_schema.tables:
            raise ValueError("No tables found in the linked schema")

        expanded_linked_schema = await self.expand_schema_async(ctx, linked_schema)

        # print(f"<query>\n{gold_query.query}\n</query>")
        # print(f"<source_columns>\n{source_columns}\n</source_columns>")
        # print(f"<schema>\n{formatter.format(ctx.db_connector.schema)}\n</schema>")
        # print(f"<linked schema>\n{formatter.format(schema)}\n</linked schema>")
        return expanded_linked_schema


PARSE_QUESTION_PROMPT = """
You are a helpful AI database expert who can analyze a given text-to-SQL question and identify the specific information pieces that must appear in the final result table.

- The output should be an ordered list of information piece descriptions.
- The information pieces must correspond exactly to the columns that should appear in the final table.
- If an information piece is ambiguous and could map to multiple columns, explicitly mention this in its description.
- To decide which information pieces are required, strictly follow the dataset and question instructions.

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
You are a helpful AI database expert who can refine the final SELECT clause of a given {{language}} query to ensure it strictly follows the dataset and question instructions.
- The revised query must return only the columns allowed and comply with all question and dataset constraints.
- You may ONLY apply the following modifications to the final SELECT clause:
  (1) Remove columns that are not in the allowed list
  (2) Reorder the columns to match the order in the allowed list
  (3) Concatenate or de-concatenate columns if there are instructions for the question or dataset
  (4) Add or remove the DISTINCT keyword
- All other modifications are forbidden. You are NOT allowed to add additional returned columns or modify existing columns in the final SELECT clause.
- If no changes are needed, return the original query unchanged.

=== START OF DATASET INSTRUCTIONS ===
{{dataset_instructions}}
=== END OF DATASET INSTRUCTIONS ===

Text-to-SQL question: {{question}}

Descriptions of the columns allowed (in order):
{{allowed_columns}}

Current {{language}} query:
{{raw_pred_query_with_exec_results}}

Your revised {{language}} query:
""".strip()


class Postprocessor:
    def __init__(self, config: BasicAgentConfig):
        self.config = config

    async def parse_question_async(self, ctx: TaskRunContext, task: SimpleNL2QTask) -> list[str]:
        class LLMOutput(BaseModel):
            information_pieces: list[str]

        agent = Agent[None, LLMOutput](  # type: ignore
            model=self.config.llm,
            output_type=LLMOutput,
            model_settings=self.config.to_model_settings(),
        )
        prompt = jinja2.Template(PARSE_QUESTION_PROMPT).render(
            dataset_instructions=task.dataset_instructions or "(no dataset instructions)",
            question=task.question + (f"\n{task.question_instructions}" if task.question_instructions else ""),
        )
        result = await agent.run(prompt)
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-PARSE-QUESTION"))
        return result.output.information_pieces  # type: ignore

    async def postprocess_async(self, ctx: TaskRunContext, task: SimpleNL2QTask, pred_query: PredQuery) -> PredQuery:
        if not task.dataset_instructions:
            return pred_query

        information_pieces = await self.parse_question_async(ctx, task)
        agent = Agent[None, str](  # type: ignore
            model=self.config.llm,
            model_settings=self.config.to_model_settings(),
        )
        prompt = jinja2.Template(POSTPROCESS_PROMPT).render(
            language=task.language,
            question=task.question + (f"\n{task.question_instructions}" if task.question_instructions else ""),
            dataset_instructions=task.dataset_instructions or "(no dataset instructions)",
            allowed_columns=information_pieces,
            raw_pred_query_with_exec_results=pred_query.to_readable(),
        )
        result = await agent.run(prompt)
        revised_pred_query = extract_code(result.output)
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-POSTPROCESS"))

        exec_result = await ctx.db_connector.run_query_async(revised_pred_query)
        if exec_result.df is None:
            return pred_query
        elif pred_query.exec_result.df is not None and len(exec_result.df.columns) > len(
            pred_query.exec_result.df.columns
        ):
            return pred_query

        return PredQuery(
            id=pred_query.id,
            query=revised_pred_query,
            parameter_names=pred_query.parameter_names,
            parameter_values=pred_query.parameter_values,
            exec_result=exec_result,
        )


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
        self.schema_linker = SchemaLinker(config)
        self.postprocessor = Postprocessor(config)

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "SQLAgent":
        return cls(config)

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        ctx = TaskRunContext(task, db_connector, Usage.create(llm=self.config.llm))

        linked_schema = await self.schema_linker.link_schema_async(ctx)

        tools: dict[str, BaseTool] = {
            "get_schema": GetSchemaTool(linked_schema, self.formatter, self.compressor),
            "get_column_description": GetColumnDescriptionTool(db_connector),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryNoParamsTool(db_connector),
            "finish": FinishTool(),
        }
        system_prompt = jinja2.Template(SQL_AGENT_SYSTEM_PROMPT).render(
            language=task.language, dataset_instructions=task.dataset_instructions
        )

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(
            f"{task.question}\n{task.question_instructions}" if task.question_instructions else task.question
        )
        raw_pred_query: PredQuery = tools["run_query"].last_pred_query()  # type: ignore
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-SQL")
        ctx.trajectories.append(trajectory)

        pred_query = await self.postprocessor.postprocess_async(ctx, task, raw_pred_query)

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
            extra_pred_info=ExtraPredInfo(
                raw_pred_query=raw_pred_query,
                linked_schema=linked_schema.get_all_column_refs(),
            ),
        )
