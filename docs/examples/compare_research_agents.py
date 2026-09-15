import asyncio

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.research.agents import BasicAgentConfig, DirectPromptAgent
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgent, SchemaLinkingAgentConfig
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx, Executable, SimpleAverageAggregator
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async


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
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
