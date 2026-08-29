import asyncio
from tabulaflow.research.observability import configure_research_observability
from tabulaflow.research.agents import SchemaLinkingAgent
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgentConfig
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx, SimpleAverageAggregator
from tabulaflow.research.pipelines import predict_async, execute_async, evaluate_async


async def main() -> None:
    configure_research_observability()
    dataloader = BirdSQLDatasetLoader()
    # dataset includes the text-to-query tasks and the database connectors
    dataset = await dataloader.get_split_async("dev")
    dataset.tasks = dataset.tasks[:3]

    # define the model arguments
    config = SchemaLinkingAgentConfig(llm="openai:gpt-4.1-mini", schema_formatter="sql_basic")
    # run the model on the dataset using async coroutines
    result = await predict_async(SchemaLinkingAgent, config, dataset, batch_size=2)
    print(result.tasks[0].pred_query.query)
    # SELECT MAX(CASE WHEN "Enrollment (K-12)" > 0 THEN "Free Meal Count (K-12)" / "Enrollment (K-12)" ELSE NULL END) AS Highest_Eligible_Free_Rate
    # FROM frpm
    # WHERE "County Name" = 'Alameda' AND "Enrollment (K-12)" > 0;
    print()
    print(result.aggregated_inference_metrics)
    # {'latency_seconds': {'avg': 7.4654, ...

    # populate exec results
    result = await execute_async(result, dataset, batch_size=2, timeout=30)

    # evaluate execution accuracy
    metrics = [BirdSQLEx()]
    result_with_metrics = await evaluate_async(
        result,
        dataset,
        metrics,
        batch_size=2,
        metric_aggregators=[SimpleAverageAggregator()],
    )
    print(result_with_metrics.aggregated_eval_metrics)
    # {'bird_sql_ex': {'avg': 0.3333}}


if __name__ == "__main__":
    asyncio.run(main())
