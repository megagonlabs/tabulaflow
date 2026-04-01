import asyncio
import copy
import json
import jinja2
import time
from dataclasses import dataclass, field
from typing import ClassVar, Any
import numpy as np
import numpy.typing as npt
from pydantic import BaseModel
from pydantic_ai import Agent
import logging
from mintq.db_connector import NL2QDBConnector
from mintq.schema import (
    ExtraPredInfo,
    NL2QDataset,
    SQLSchema,
    SQLTableSchema,
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
    PredQuery,
    Usage,
    Trajectory,
    ColumnRef,
)
from mintq.preprocessors import ERDiagramSynthesizer, QuestionEmbedder, SchemaPreprocessor
from mintq.toolhub import (
    BaseTool,
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
)
from mintq.formatters.base import formatter_registry, NL2QFormatter
from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import (
    get_max_steps_processor,
    instrument,
    BasicAgentConfig,
    TaskRunContext,
)
from mintq.utils import extract_code, extract_all_source_columns
from mintq.preprocessors.er_diagram import ERDiagram
from mintq.formatters.er_diagram import ERDiagramMermaidFormatter


logger = logging.getLogger(__name__)


class SQLAgentConfig(BasicAgentConfig):
    min_columns_for_schema_linking: int = 20
    num_few_shot_examples: int = 0
    do_schema_linking: bool = True
    do_postprocessing: bool = True
    question_embedder_embedding_llm: str = "openai:text-embedding-3-small"


def format_question(task: SimpleNL2QTask) -> str:
    res = task.question
    if task.question_instructions:
        res += "\n" + task.question_instructions
    return res


@dataclass
class SQLAgentContext(TaskRunContext):
    er_diagram: ERDiagram | None = None
    er_diagram_formatter: ERDiagramMermaidFormatter | None = None
    few_shot_examples: list[SimpleNL2QTask] = field(default_factory=list)


# <resolving_ambiguity>
# Always try to identify the ambiguities in the question before writing queries:
# - If a term or phrase is ambiguous, explicitly reason about all possible interpretations and select the most likely one.
# - You may execute multiple alternative queries and choose the most reasonable one based on the execution results.
# - Do not ask the user clarification questions. Proceed using the information provided and resolve the ambiguity yourself.
# - The most common forms of ambiguity are:
#   - Column Ambiguity: A term in the question can map to multiple possible columns.
#   - Table Ambiguity: A referenced entity can map to more than one table.
#   - Value Ambiguity: Query terms can match multiple values in a column, or describe vague concepts without clear boundaries.
#   - Computation Ambiguity: Required operations or metrics can be computed in multiple legitimate ways, producing distinct results.
# - If there is no ambiguity, acknowledge in your reasoning that the question is unambiguous.
# </resolving_ambiguity>


SQL_AGENT_SYSTEM_PROMPT = """
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
- You may call the `run_query` tool multiple times while building the final query.
- You may execute intermediate or exploratory queries; however, the final query (the last one executed) must be complete and fully constructed. In the final query, do not split the logic into multiple dependent queries (for example, first retrieving an ID and then using that ID in a subsequent query—this is not allowed).
- You may use the `search_keywords` tool to search for multiple keywords within a column.
- Be THOROUGH when constructing the final query. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{dataset_instructions}}
</dataset_instructions>
{%- endif %}
{%- if examples %}

<examples>
Here are some similar questions and their correct SQL queries for reference:
{% for example in examples %}
Question: {{example.question}} {{example.question_instructions}}
SQL: {{example.gold_query.query}}
{% endfor -%}
</examples>
{%- endif %}

<conceptual_er_diagram>
{{er_diagram}}
</conceptual_er_diagram>

<physical_database_schema>
{{schema}}
</physical_database_schema>
{%- if document %}

<document>
{{document}}
</document>
{%- endif %}
""".strip()

EXPAND_COLUMNS_PROMPT = """
You are a helpful AI database expert.
Given a list of columns that can be used to answer a question, identify potential alternative columns for each of the given columns.

- All table and column names must exactly match those in the database schema.
- The alternative columns can be from the same table or different tables.
- The alternative columns can be an empty list if there are no alternatives.

<example>
Question: "What is the date of order 1005?"
Columns: [{schema_name: null, table_name: "order", column_name: "order_date"}]
Output:
[
  {
    "original_column": {
      "schema_name": null,
      "table_name": "order",
      "column_name": "order_date"
    },
    "alternatives": [
      {
        "schema_name": null,
        "table_name": "order",
        "column_name": "shipping_date"
      }
    ]
  }
]
</example>

===== Your Task =====
{%- if document %}

<document>
{{document}}
</document>
{%- endif %}

<database_schema>
{{schema}}
</database_schema>

Question: {{question}}

Columns:
{{columns}}

Your output:
""".strip()


class SchemaLinker:
    def __init__(self, config: SQLAgentConfig):
        self.config = config

    async def _generate_sql_async(self, ctx: SQLAgentContext, task: SimpleNL2QTask) -> PredQuery:
        db_connector = ctx.db_connector

        tools: dict[str, BaseTool] = {
            # "get_schema": GetSchemaTool(ctx.preprocessed_schema, ctx.schema_formatter),
            # "get_column_description": GetColumnDescriptionTool(ctx.preprocessed_schema),
            "search_keywords": SearchKeywordsTool(db_connector),  # type: ignore[arg-type]
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }
        system_prompt = jinja2.Template(SQL_AGENT_SYSTEM_PROMPT).render(
            language=ctx.db_connector.language,
            dataset_instructions=task.dataset_instructions,
            schema=ctx.schema_formatter.format(
                ctx.preprocessed_schema, add_description=self.config.use_column_description
            ),
            er_diagram=ctx.er_diagram_formatter.format(ctx.er_diagram) if ctx.er_diagram is not None else None,  # type: ignore
            document=task.document,
            examples=ctx.few_shot_examples,
        )

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
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-SCHEMA-LINK-SQL")
        ctx.trajectories.append(trajectory)
        return pred_query

    async def expand_schema_async(
        self, ctx: SQLAgentContext, schema_to_expand: SQLSchema, task: SimpleNL2QTask, batch_size: int = 5
    ) -> SQLSchema:
        class ColumnWithAlternatives(BaseModel):
            original_column: ColumnRef
            alternatives: list[ColumnRef]

        class LLMOutput(BaseModel):
            results: list[ColumnWithAlternatives]

        current_columns = schema_to_expand.get_all_column_refs()

        async def process_batch_async(batch_idx: int, batch: list[ColumnRef]) -> list[ColumnWithAlternatives]:
            agent = Agent[None, LLMOutput](  # type: ignore
                model=self.config.llm,
                output_type=LLMOutput,
                model_settings=self.config.to_model_settings(),
            )
            prompt = jinja2.Template(EXPAND_COLUMNS_PROMPT).render(
                schema=ctx.schema_formatter.format(ctx.preprocessed_schema),
                question=format_question(task),
                columns=json.dumps(
                    [
                        {"schema_name": c.schema_name, "table_name": c.table_name, "column_name": c.column_name}
                        for c in batch
                    ],
                    indent=2,
                ),
                document=task.document,
            )
            result = await agent.run(prompt)
            ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
            ctx.trajectories.append(
                Trajectory.from_pydantic_ai_messages(result.all_messages(), id=f"TRJY-EXPAND-SCHEMA-{batch_idx}")
            )
            return result.output.results  # type: ignore

        batches = [current_columns[i : i + batch_size] for i in range(0, len(current_columns), batch_size)]
        all_results = await asyncio.gather(*[process_batch_async(i, batch) for i, batch in enumerate(batches)])

        linked = set((c.schema_name, c.table_name, c.column_name) for c in current_columns) | {
            (alt.schema_name, alt.table_name, alt.column_name)
            for results in all_results
            for item in results
            for alt in item.alternatives
        }
        linked_column_refs = [ColumnRef(schema_name=s, table_name=t, column_name=c) for s, t, c in linked]
        linked_schema = ctx.preprocessed_schema.trim(linked_column_refs, case_insensitive=True, keep_pk=True)
        return linked_schema

    async def link_schema_async(self, ctx: SQLAgentContext, task: SimpleNL2QTask) -> SQLSchema:
        if ctx.preprocessed_schema.num_total_columns() < self.config.min_columns_for_schema_linking:
            return ctx.preprocessed_schema

        pred_query = await self._generate_sql_async(ctx, task)
        # pred_query = ctx.task.gold_query

        source_columns = set(
            (c[0].lower(), c[1].lower())
            for c in extract_all_source_columns(pred_query.query, language=ctx.db_connector.language)
        )

        linked_schema = copy.deepcopy(ctx.preprocessed_schema)
        for table in linked_schema.tables:
            table.columns = [col for col in table.columns if (table.name.lower(), col.name.lower()) in source_columns]
        linked_schema.tables = [table for table in linked_schema.tables if table.columns]

        if not linked_schema.tables:
            logger.warning(
                f"No tables found in the linked schema. Pred query: {pred_query.query}. Extracted source columns: {source_columns}. "
            )
            return ctx.preprocessed_schema

        expanded_linked_schema = await self.expand_schema_async(ctx, linked_schema, task)

        # print(f"<query>\n{gold_query.query}\n</query>")
        # print(f"<source_columns>\n{source_columns}\n</source_columns>")
        # print(f"<schema>\n{formatter.format(ctx.db_connector.schema)}\n</schema>")
        # print(f"<linked schema>\n{formatter.format(schema)}\n</linked schema>")
        return expanded_linked_schema


POSTPROCESS_PROMPT = """
You are a helpful AI database expert who can refine the final SELECT clause of a given {{language}} query to ensure it strictly follows the dataset and question instructions.
- You may ONLY apply the following modifications to **the final SELECT clause**:
  (1) Remove columns.
  (2) Reorder the columns.
  (3) De-concatenate columns.
  (4) Add or remove the DISTINCT keyword.
  (5) Rounding of numeric values.
  (6) Move the placement of * 100.0 in percentage calculations from denominator to numerator or vice versa. However, you cannot introduce or remove * 100.0.
- If you remove an aliased column that is referenced in other clauses (e.g., ORDER BY, HAVING), you are allowed to modify those clauses to keep the query executable.
- All other modifications are forbidden.
  - You are NOT allowed to add additional returned columns or modify existing columns in the final SELECT clause.
  - You are NOT allowed to modify other clauses except for the reason mentioned above.
- If no changes are needed, return the original query unchanged.

{%- if examples %}

<examples>
Here are some similar questions and their correct SQL queries for reference:
{% for example in examples %}
Question: {{example.question}} {{example.question_instructions}}
SQL: {{example.gold_query.query}}
{% endfor -%}
</examples>
{%- endif %}

===== Your Task =====
{%- if dataset_instructions %}

<dataset_instructions>
{{dataset_instructions}}
</dataset_instructions>
{%- endif %}

Text-to-SQL question: {{question}}

Current {{language}} query:
{{raw_pred_query_with_exec_results}}

Your revised {{language}} query:
""".strip()


class Postprocessor:
    def __init__(self, config: SQLAgentConfig):
        self.config = config

    async def postprocess_async(self, ctx: SQLAgentContext, task: SimpleNL2QTask, pred_query: PredQuery) -> PredQuery:
        # if not task.dataset_instructions:
        #     return pred_query

        agent = Agent[None, str](  # type: ignore
            model=self.config.llm,
            model_settings=self.config.to_model_settings(),
        )
        prompt = jinja2.Template(POSTPROCESS_PROMPT).render(
            language=ctx.db_connector.language,
            question=format_question(task),
            dataset_instructions=task.dataset_instructions or "(no dataset instructions)",
            examples=ctx.few_shot_examples,
            raw_pred_query_with_exec_results=pred_query.to_markdown(),
        )
        result = await agent.run(prompt)
        revised_pred_query = extract_code(result.output)
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        ctx.trajectories.append(Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-POSTPROCESS"))

        if pred_query.exec_result is None:
            pred_query.exec_result = await ctx.db_connector.run_query_async(pred_query.query)

        revised_exec_result = await ctx.db_connector.run_query_async(revised_pred_query)
        if revised_exec_result.df is None:
            return pred_query
        elif pred_query.exec_result.df is not None and len(revised_exec_result.df.columns) > len(
            pred_query.exec_result.df.columns
        ):  # We do not allow adding columns
            return pred_query

        return PredQuery(
            id=pred_query.id,
            query=revised_pred_query,
            parameter_names=pred_query.parameter_names,
            parameter_values=pred_query.parameter_values,
            exec_result=revised_exec_result,
        )


@agent_registry.register
class SQLAgent:
    name: ClassVar = "sql_agent"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = SQLAgentConfig

    def __init__(
        self,
        config: SQLAgentConfig,
        few_shot_dataset: NL2QDataset | None = None,
        few_shot_embeddings: npt.NDArray[Any] | None = None,
    ):
        self.config = config
        self.few_shot_dataset = few_shot_dataset
        self.few_shot_embeddings = few_shot_embeddings

        self.formatter: NL2QFormatter = formatter_registry.get_class(config.schema_formatter)(
            **config.to_formatter_kwargs()
        )
        self.schema_linker = SchemaLinker(config) if config.do_schema_linking else None
        self.postprocessor = Postprocessor(config) if config.do_postprocessing else None

    @classmethod
    async def from_config_async(cls, config: SQLAgentConfig, few_shot_dataset: NL2QDataset | None = None) -> "SQLAgent":
        if config.num_few_shot_examples > 0:
            if few_shot_dataset is None:
                raise ValueError("few_shot_dataset is required when num_few_shot_examples is greater than 0")
            question_embedder = QuestionEmbedder(embedding_llm=config.question_embedder_embedding_llm)
            few_shot_embeddings, _ = await question_embedder.preprocess_async(few_shot_dataset)
        else:
            few_shot_embeddings = None
        return cls(config, few_shot_dataset, few_shot_embeddings)

    def _sort_tables(self, preprocessed_schema: SQLSchema, er_diagram: ERDiagram) -> SQLSchema:
        """Reorder the tables in preprocessed_schema to match the order in er_diagram"""
        er_table_order: dict[tuple[str | None, str], int] = {}
        for entity in er_diagram.conceptual_entities:
            for source_table in entity.source_tables:
                key = (source_table.schema_name, source_table.table_name)
                if key not in er_table_order:
                    er_table_order[key] = len(er_table_order)

        def get_table_sort_key(table: SQLTableSchema) -> tuple[int, int]:
            key = (table.schema_name, table.name)
            if key in er_table_order:
                return (0, er_table_order[key])
            return (1, 0)  # Tables not in ER diagram go to the end

        preprocessed_schema.tables.sort(key=get_table_sort_key)
        return preprocessed_schema

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: NL2QDBConnector) -> SimpleNL2QTaskOutput:
        if not isinstance(db_connector.schema, SQLSchema):
            raise TypeError(f"SQLAgent requires a SQL db connector, got {type(db_connector)!r}")
        t0 = time.time()

        schema_preprocessor = SchemaPreprocessor()
        preprocessed_schema = await schema_preprocessor.preprocess_async(db_connector)
        question_embedder = QuestionEmbedder(embedding_llm=self.config.question_embedder_embedding_llm)
        er_diagram_synthesizer = ERDiagramSynthesizer()
        er_diagram = await er_diagram_synthesizer.preprocess_async(db_connector)
        er_diagram_formatter = ERDiagramMermaidFormatter()

        preprocessed_schema = self._sort_tables(preprocessed_schema, er_diagram)

        examples: list[SimpleNL2QTask] = []
        if self.config.num_few_shot_examples > 0:
            vec, _ = await question_embedder.embed_task_async(task)

            # Compute cosine similarity between task embedding and few-shot embeddings
            # Normalize embeddings for cosine similarity
            vec_norm = vec / np.linalg.norm(vec)
            few_shot_norms = self.few_shot_embeddings / np.linalg.norm(self.few_shot_embeddings, axis=1, keepdims=True)  # type: ignore
            similarities = np.dot(few_shot_norms, vec_norm)
            # Get top-k most similar example indices
            top_k_indices = np.argsort(similarities)[::-1][: self.config.num_few_shot_examples]
            examples = [self.few_shot_dataset.tasks[i] for i in top_k_indices]  # type: ignore

        ctx = SQLAgentContext(
            task=task,
            db_connector=db_connector,
            preprocessed_schema=preprocessed_schema,
            schema_formatter=self.formatter,  # type: ignore[arg-type]
            usage=Usage.create(llm=self.config.llm),
            tools={},
            trajectories=[],
            er_diagram=er_diagram,
            er_diagram_formatter=er_diagram_formatter,
            few_shot_examples=examples,
        )
        ctx.usage += er_diagram_synthesizer.usage()
        ctx.usage += schema_preprocessor.usage()
        ctx.usage += question_embedder.usage()

        ##### Remove #####
        # if hasattr(task, "pred_query") and task.pred_query is not None:
        #     from mintq.datahub.bird_sql import BIRD_DATASET_INSTRUCTIONS

        #     task.dataset_instructions = BIRD_DATASET_INSTRUCTIONS
        #     postprocessed_pred_query = await self.postprocessor.postprocess_async(
        #         ctx, task, task.extra_pred_info.raw_pred_query
        #     )
        #     task.pred_query = postprocessed_pred_query
        #     task.trajectory = ctx.trajectories
        #     return task
        ##################

        if self.schema_linker is not None:
            linked_schema = await self.schema_linker.link_schema_async(ctx, task)
        else:
            linked_schema = ctx.preprocessed_schema
        linked_er_diagram = ctx.er_diagram.trim(linked_schema.get_all_table_refs(), case_insensitive=True)  # type: ignore

        tools: dict[str, BaseTool] = {
            # "get_schema": GetSchemaTool(linked_schema, self.formatter),
            # "get_column_description": GetColumnDescriptionTool(linked_schema),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }
        system_prompt = jinja2.Template(SQL_AGENT_SYSTEM_PROMPT).render(
            language=db_connector.language,
            dataset_instructions=task.dataset_instructions,
            schema=self.formatter.format(linked_schema, add_description=self.config.use_column_description),  # type: ignore[arg-type, call-arg]
            er_diagram=ctx.er_diagram_formatter.format(linked_er_diagram),  # type: ignore
            document=task.document,
            examples=examples,
        )

        agent = Agent[None, None](  # type: ignore
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(format_question(task))
        raw_pred_query: PredQuery = tools["run_query"].last_pred_query()  # type: ignore
        ctx.usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-SQL")
        ctx.trajectories.append(trajectory)

        if self.postprocessor is not None:
            pred_query = await self.postprocessor.postprocess_async(ctx, task, raw_pred_query)
        else:
            pred_query = raw_pred_query

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
