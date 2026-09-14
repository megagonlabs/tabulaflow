import asyncio

from tabulaflow.research.agents import BasicAgentConfig, FullSchemaAgent
from tabulaflow.research.benchmarks.bird_sql import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.pipelines.execute import execute_async
from tabulaflow.research.pipelines.predict import predict_async
from tabulaflow.research.types import SimpleNL2QTaskOutput


async def main() -> None:
    # Load three tasks and their database from BIRD-SQL.
    dataset = await BirdSQLDatasetLoader().get_split_async(
        "dev",
        databases=["california_schools"],
        subsample_size=3,
    )

    # Run one full-schema agent per task, concurrently.
    result = await predict_async(
        FullSchemaAgent,
        BasicAgentConfig(),
        dataset,
        batch_size=3,
    )
    # Execute predicted queries if their results are missing.
    await execute_async(result, dataset, batch_size=3)
    first = result.tasks[0]
    assert isinstance(first, SimpleNL2QTaskOutput)
    assert first.pred_query is not None
    assert first.pred_query.exec_result is not None
    print("Question:", first.question)
    print("Predicted SQL:", first.pred_query.query)
    print("Query result:")
    print(first.pred_query.exec_result.df)

    await evaluate_async(result, dataset, metrics=[BirdSQLEx()], batch_size=3)
    print("Execution accuracy:", result.aggregated_eval_metrics["bird_sql_ex"]["avg"])
    await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
