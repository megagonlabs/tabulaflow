import asyncio
from collections.abc import Mapping

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.data import DataConnector
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgent, SchemaLinkingAgentConfig
from tabulaflow.research.benchmarks.bird_sql import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx, Executable, PredSuccess, SimpleAverageAggregator
from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.pipelines.execute import execute_async
from tabulaflow.research.pipelines.predict import predict_async


async def close_connectors(connectors: Mapping[str, DataConnector]) -> None:
    await asyncio.gather(*(connector.close_async() for connector in connectors.values()))


async def main() -> None:
    initialize_agent_runtime(AgentRuntimeConfig(preprocessing_cache_mode="read_write"))
    loader = BirdSQLDatasetLoader()
    dataset = await loader.get_split_async("dev", subsample_size=3)

    try:
        result = await predict_async(
            agent_cls=SchemaLinkingAgent,
            agent_config=SchemaLinkingAgentConfig(
                llm="openai-responses:gpt-5-mini",
                num_few_shot_examples=0,
            ),
            dataset=dataset,
            batch_size=3,
        )
        await execute_async(result, dataset, batch_size=3)
        await evaluate_async(
            result,
            dataset,
            metrics=[BirdSQLEx(), Executable(), PredSuccess()],
            batch_size=3,
            metric_aggregators=[SimpleAverageAggregator()],
        )
        result.to_directory(
            "runs/bird-schema-linking",
            eval_metrics_in_summary=["bird_sql_ex", "executable", "pred_success"],
        )
        metrics = result.aggregated_eval_metrics
        cost = 0 if result.total_usage is None else result.total_usage.api_cost_usd
        print("BIRD-SQL / dev")
        print("Agent: schema_linking")
        print(f"Tasks: {len(result.tasks)}")
        print(f"Execution accuracy: {metrics['bird_sql_ex']['avg']:.2f}")
        print(f"Executable: {metrics['executable']['avg']:.2f}")
        print(f"Prediction success: {metrics['pred_success']['avg']:.2f}")
        print(f"Estimated cost: ${cost:.4f}")
        print("Saved to: runs/bird-schema-linking")
    finally:
        await close_connectors(dataset.db_connectors)


if __name__ == "__main__":
    asyncio.run(main())
