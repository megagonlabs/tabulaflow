# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pydantic>=2.12"]
# ///

import asyncio

# --8<-- [start:agent-imports]
from typing import ClassVar

from pydantic import BaseModel, Field

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.trace import Trajectory, Usage
from tabulaflow.core import SQLSchema, TableRef
from tabulaflow.data import DataConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter
from tabulaflow.research.types import PredQuery, SimpleNL2QTask, SimpleNL2QTaskOutput
# --8<-- [end:agent-imports]

from tabulaflow.research.benchmarks import BirdSQLDatasetLoader

# --8<-- [start:pipeline-imports]
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async
# --8<-- [end:pipeline-imports]


# --8<-- [start:agent]
class TableLinkingConfig(BaseModel):
    llm: str = "openai-responses:gpt-5-mini"


class TableSelection(BaseModel):
    tables: list[TableRef] = Field(min_length=1)


class SQLPrediction(BaseModel):
    query: str = Field(min_length=1, description="The SQL query answering the question.")


class TableLinkingAgent:
    """Select relevant tables, then generate SQL from their schema."""

    name: ClassVar[str] = "table_linking"
    task_type: ClassVar[str] = "simple"
    output_type: ClassVar[str] = "simple"
    config_cls: ClassVar[type[TableLinkingConfig]] = TableLinkingConfig

    def __init__(self, config: TableLinkingConfig):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: TableLinkingConfig) -> "TableLinkingAgent":
        return cls(config)

    async def predict_async(self, task: SimpleNL2QTask, db_connector: DataConnector) -> SimpleNL2QTaskOutput:
        if not isinstance(db_connector.schema, SQLSchema):
            raise TypeError("TableLinkingAgent requires a SQL database.")
        schema = db_connector.schema
        formatter = SQLDDLSchemaFormatter()
        prompt = task.model_dump_json(
            include={"question", "question_instructions", "dataset_instructions", "document"},
            exclude_none=True,
        )

        table_linker = make_agent(
            self.config.llm,
            output_type=TableSelection,
            instructions="Select the tables needed to answer the question, including tables needed for joins. "
            "Use exact schema and table names, with schema_name=null for unqualified tables.\n"
            f"Database schema:\n{formatter.format(schema, include_descriptions=True)}",
        )
        selection = await table_linker.run(prompt)
        tables_by_ref = {(table.schema_name, table.name): table for table in schema.tables}
        selected_tables = [tables_by_ref[(ref.schema_name, ref.table_name)] for ref in selection.output.tables]
        linked_schema = schema.model_copy(update={"tables": selected_tables})

        sql_generator = make_agent(
            self.config.llm,
            output_type=SQLPrediction,
            instructions=f"Answer the question with a {db_connector.language} query using only the provided tables.\n"
            f"Database schema:\n{formatter.format(linked_schema, include_descriptions=True)}",
        )
        prediction = await sql_generator.run(prompt)
        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=PredQuery(query=prediction.output.query),
            usage=(
                Usage.from_pydantic_ai_usage(selection.usage, self.config.llm)
                + Usage.from_pydantic_ai_usage(prediction.usage, self.config.llm)
            ),
            trajectory=[
                Trajectory.from_pydantic_ai_messages(selection.all_messages(), id="TRJY-TABLE-LINKING"),
                Trajectory.from_pydantic_ai_messages(prediction.all_messages(), id="TRJY-SQL-GENERATION"),
            ],
        )


# --8<-- [end:agent]


async def main() -> None:
    dataset = await BirdSQLDatasetLoader().get_split_async("dev", databases=["california_schools"], subsample_size=3)
    try:
        # --8<-- [start:integration]
        result = await predict_async(TableLinkingAgent, TableLinkingConfig(), dataset, batch_size=3)
        await execute_async(result, dataset, batch_size=3)
        await evaluate_async(result, dataset, metrics=[BirdSQLEx()], batch_size=3)
        # --8<-- [end:integration]
        result.to_directory("runs/table_linking")
        print(result.aggregated_eval_metrics)
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
