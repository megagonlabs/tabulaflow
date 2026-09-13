import asyncio
from collections.abc import Mapping

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.data import DataConnector
from tabulaflow.research.agents.direct_prompt import DirectPromptAgent
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgent
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgentConfig
from tabulaflow.research.agents.utils import BasicAgentConfig
from tabulaflow.research.benchmarks.bird_sql import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx, Executable, SimpleAverageAggregator
from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.pipelines.execute import execute_async
from tabulaflow.research.pipelines.predict import predict_async


async def close_connectors(connectors: Mapping[str, DataConnector]) -> None:
    await asyncio.gather(*(connector.close_async() for connector in connectors.values()))


async def main() -> None:
    initialize_agent_runtime(AgentRuntimeConfig(preprocessing_cache_mode="read_write"))
    dataset = await BirdSQLDatasetLoader().get_split_async("dev", subsample_size=5)
    strategies = [
        ("direct_prompting", DirectPromptAgent, BasicAgentConfig(llm="openai-responses:gpt-5-mini")),
        (
            "schema_linking",
            SchemaLinkingAgent,
            SchemaLinkingAgentConfig(llm="openai-responses:gpt-5-mini", num_few_shot_examples=0),
        ),
    ]

    try:
        for name, agent_cls, config in strategies:
            result = await predict_async(agent_cls, config, dataset, batch_size=5)
            await execute_async(result, dataset, batch_size=5)
            await evaluate_async(
                result,
                dataset,
                metrics=[BirdSQLEx(), Executable()],
                batch_size=5,
                metric_aggregators=[SimpleAverageAggregator()],
            )
            result.to_directory(
                f"runs/{name}",
                eval_metrics_in_summary=["bird_sql_ex", "executable"],
            )
            print(name, result.aggregated_eval_metrics)
    finally:
        await close_connectors(dataset.db_connectors)


if __name__ == "__main__":
    asyncio.run(main())
