import asyncio
from typing import ClassVar

from pydantic import BaseModel, Field

from tabulaflow.agents.llm import make_agent
from tabulaflow.core import SQLSchema
from tabulaflow.data import DataConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter
from tabulaflow.research.agents.utils import BasicAgentConfig, format_question
from tabulaflow.research.benchmarks.bird_sql import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.pipelines.execute import execute_async
from tabulaflow.research.pipelines.predict import predict_async
from tabulaflow.research.types import ExtraPredInfo, PredQuery, SimpleNL2QTask, SimpleNL2QTaskOutput


class QueryPrediction(BaseModel):
    # Structured model output replaces parsing text or JSON by hand.
    relevant_tables: list[str] = Field(description="Tables needed to answer the question")
    query: str = Field(description="One executable SQL query")


class PlanAndQueryAgent:
    # These attributes declare compatibility with the research pipeline.
    name: ClassVar[str] = "plan_and_query"
    task_type: ClassVar[str] = "simple"
    output_type: ClassVar[str] = "simple"
    config_cls: ClassVar[type[BasicAgentConfig]] = BasicAgentConfig

    def __init__(self, config: BasicAgentConfig) -> None:
        self.config = config

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "PlanAndQueryAgent":
        return cls(config)

    async def predict_async(
        self,
        task: SimpleNL2QTask,
        db_connector: DataConnector,
    ) -> SimpleNL2QTaskOutput:
        if not isinstance(db_connector.schema, SQLSchema):
            raise TypeError("PlanAndQueryAgent requires a SQL database")

        schema = SQLDDLSchemaFormatter().format(db_connector.schema)
        agent = make_agent(
            self.config.llm,
            output_type=QueryPrediction,
            instructions=(
                "Select the tables needed to answer the question, then write one executable SQL query.\n\n"
                f"Dataset instructions:\n{task.dataset_instructions or 'None'}\n\n"
                f"Database schema:\n{schema}"
            ),
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(format_question(task))
        prediction = result.output

        # Adapt the method-specific output to the shared benchmark result type.
        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=PredQuery(query=prediction.query),
            extra_pred_info=ExtraPredInfo(other={"relevant_tables": prediction.relevant_tables}),
        )


async def main() -> None:
    # A loader returns typed tasks and the live connectors they require.
    dataset = await BirdSQLDatasetLoader().get_split_async(
        "dev",
        databases=["california_schools"],
        subsample_size=3,
    )

    first_task = dataset.tasks[0]
    schema = dataset.db_connectors[first_task.db].schema
    assert isinstance(schema, SQLSchema)
    print(f"Loaded {len(dataset.tasks)} BIRD-SQL tasks")
    print("Question:", first_task.question)
    print("Schema tables:", [table.name for table in schema.tables])

    # The pipeline runs one custom agent per task, concurrently.
    result = await predict_async(
        PlanAndQueryAgent,
        BasicAgentConfig(),
        dataset,
        batch_size=3,
    )

    # Method-specific data remains available on the typed task output.
    first = result.tasks[0]
    assert isinstance(first, SimpleNL2QTaskOutput)
    assert first.pred_query is not None
    print("\nRelevant tables:", first.extra_pred_info.other["relevant_tables"])
    print("Predicted SQL:", first.pred_query.query)

    # Execution attaches an ExecResult to each query; successful results include a DataFrame.
    await execute_async(result, dataset, batch_size=3)
    execution = first.pred_query.exec_result
    assert execution is not None
    if execution.error is not None:
        print("\nExecution failed:", execution.error.message)
    elif execution.df is not None:
        rows, columns = execution.df.shape
        print(f"\nQuery result: {rows} rows × {columns} columns")
        print(execution.df.head())

    # Metrics consume the same typed run, independently of the agent.
    await evaluate_async(
        result,
        dataset,
        metrics=[BirdSQLEx()],
        batch_size=3,
    )
    print("\nExecution accuracy:", result.aggregated_eval_metrics["bird_sql_ex"]["avg"])

    await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
