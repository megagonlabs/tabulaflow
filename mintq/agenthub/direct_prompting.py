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
from mintq.db_connector import BaseSQLDBConnector
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
from mintq.preprocessors import ERDiagramSynthesizer, QuestionEmbedder, SchemaCompressor, SchemaPreprocessor
from mintq.toolhub import (
    BaseTool,
    RunQueryNoParamsTool,
    SearchKeywordsTool,
    FinishTool,
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
from mintq.preprocessors.er_diagram import ERDiagram
from mintq.formatters.er_diagram import ERDiagramMermaidFormatter


logger = logging.getLogger(__name__)


def format_question(task: SimpleNL2QTask) -> str:
    res = task.question
    if task.question_instructions:
        res += "\n" + task.question_instructions
    return res


SQL_AGENT_SYSTEM_PROMPT = """
You a helpful AI database expert that writes {{language}} queries given a user question.

<goal>
- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information and follow the most natural interpretation.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Pay close attention to detail. When multiple similar columns exist, select the one that best matches the question and the instructions.
- Follow the dataset and question instructions if they are provided. When there is a conflict between instructions, prioritize the question instructions.
</goal>
{%- if dataset_instructions %}

<dataset_instructions>
{{dataset_instructions}}
</dataset_instructions>
{%- endif %}

<physical_database_schema>
{{schema}}
</physical_database_schema>
{%- if document %}

<document>
{{document}}
</document>
{%- endif %}
""".strip()


@agent_registry.register
class DirectPrompting:
    name: ClassVar = "direct_prompting"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = BasicAgentConfig

    def __init__(
        self,
        config: BasicAgentConfig,
    ):
        self.config = config
        self.compressor = SchemaCompressor() if config.compress_schema else None
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "DirectPrompting":
        return cls(config)

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        schema = db_connector.schema
        if self.config.compress_schema:
            schema = SchemaCompressor().compress(schema)
        schema_str = self.formatter.format(schema)

        system_prompt = jinja2.Template(SQL_AGENT_SYSTEM_PROMPT).render(
            language=task.language,
            dataset_instructions=task.dataset_instructions,
            schema=schema_str,
            document=task.document,
        )

        agent = Agent[None, str](  # type: ignore
            model=self.config.llm,
            instructions=system_prompt,
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(format_question(task))
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-SQL")
        pred_query = PredQuery(query=extract_code(result.output))

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0

        return SimpleNL2QTaskOutput(
            **task.model_dump(), pred_query=pred_query, trajectory=trajectory, usage=usage, inference_metrics=metrics
        )
