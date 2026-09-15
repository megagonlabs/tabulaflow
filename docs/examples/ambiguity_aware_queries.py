# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0"]
# ///

import asyncio

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.research.agents.ambig_structured import AmbigStructuredSQLAgent, AmbigStructuredSQLAgentConfig
from tabulaflow.research.benchmarks import ARCSDatasetLoader
from tabulaflow.research.metrics import Executable, FoundOne, SimpleEx
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async


async def main() -> None:
    initialize_agent_runtime(AgentRuntimeConfig(preprocessing_cache_mode="read_write"))
    dataset = await ARCSDatasetLoader().get_split_async("test", qids=["001-5"])

    try:
        # --8<-- [start:prediction]
        result = await predict_async(
            agent_cls=AmbigStructuredSQLAgent,
            agent_config=AmbigStructuredSQLAgentConfig(
                llm="openai-responses:gpt-4.1",
                query_for_intended_only=True,
            ),
            dataset=dataset,
            batch_size=1,
        )
        # --8<-- [end:prediction]
        await execute_async(result, dataset, batch_size=1)
        await evaluate_async(
            result,
            dataset,
            metrics=[SimpleEx(), Executable(), FoundOne()],
            batch_size=1,
        )
        result.to_directory(
            "runs/arcs-structured",
            eval_metrics_in_summary=["simple_ex", "executable", "found_one"],
        )
        for task in result.tasks:
            print(task.to_markdown())
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
