import asyncio

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.research.agents.ambig_structured import AmbigStructuredSQLAgent, AmbigStructuredSQLAgentConfig
from tabulaflow.research.benchmarks import AmbrosiaSDatasetLoader
from tabulaflow.research.metrics import Executable, FoundOne, SimpleAverageAggregator, SimpleEx
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async


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
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
