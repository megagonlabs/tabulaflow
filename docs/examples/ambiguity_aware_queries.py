import asyncio
from collections.abc import Mapping

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.data import DataConnector
from tabulaflow.research.agents.ambig_structured import AmbigStructuredSQLAgent, AmbigStructuredSQLAgentConfig
from tabulaflow.research.benchmarks.ambrosia_s import AmbrosiaSDatasetLoader
from tabulaflow.research.metrics import Executable, FoundOne, SimpleAverageAggregator, SimpleEx
from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.pipelines.execute import execute_async
from tabulaflow.research.pipelines.predict import predict_async


async def close_connectors(connectors: Mapping[str, DataConnector]) -> None:
    await asyncio.gather(*(connector.close_async() for connector in connectors.values()))


async def main() -> None:
    initialize_agent_runtime(AgentRuntimeConfig(preprocessing_cache_mode="read_write"))
    dataset = await AmbrosiaSDatasetLoader().get_split_async("test", subsample_size=2)

    try:
        result = await predict_async(
            agent_cls=AmbigStructuredSQLAgent,
            agent_config=AmbigStructuredSQLAgentConfig(
                llm="openai-responses:gpt-5-mini",
                query_for_intended_only=False,
            ),
            dataset=dataset,
            batch_size=2,
        )
        await execute_async(result, dataset, batch_size=2)
        await evaluate_async(
            result,
            dataset,
            metrics=[SimpleEx(), Executable(), FoundOne()],
            batch_size=2,
            metric_aggregators=[SimpleAverageAggregator()],
        )
        result.to_directory(
            "runs/ambrosia-structured",
            eval_metrics_in_summary=["simple_ex", "executable", "found_one"],
        )
        for task in result.tasks:
            print(task.to_markdown())
    finally:
        await close_connectors(dataset.db_connectors)


if __name__ == "__main__":
    asyncio.run(main())
