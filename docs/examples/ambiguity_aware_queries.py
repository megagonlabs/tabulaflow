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
from tabulaflow.research.types import StructuredAmbigNL2QTaskOutput


async def main() -> None:
    initialize_agent_runtime(AgentRuntimeConfig(preprocessing_cache_mode="read_write"))
    # --8<-- [start:load]
    dataset = await ARCSDatasetLoader().get_split_async("test", qids=["001-5"])
    # --8<-- [end:load]

    try:
        # --8<-- [start:prediction]
        print("Question:", dataset.tasks[0].question)

        result = await predict_async(
            agent_cls=AmbigStructuredSQLAgent,
            agent_config=AmbigStructuredSQLAgentConfig(
                llm="openai-responses:gpt-4.1",
                query_for_intended_only=True,
            ),
            dataset=dataset,
            batch_size=1,
            verbose=False,
        )

        task = result.tasks[0]
        assert isinstance(task, StructuredAmbigNL2QTaskOutput)
        for ap in task.pred_finite_ambiguity_points:
            print(f"\n{ap.phrase}:")
            for index, interpretation in enumerate(ap.interpretations):
                selected = " (selected)" if index == ap.intended_interpretation_idx else ""
                print(f"  {ap.id}.{index}: {interpretation}{selected}")

        prediction = task.pred_intended_query
        print("\nPredicted SQL:")
        print(prediction.query if prediction is not None else "No query returned.")
        # --8<-- [end:prediction]
        await execute_async(result, dataset, batch_size=1, verbose=False)
        await evaluate_async(
            result,
            dataset,
            metrics=[SimpleEx(), Executable(), FoundOne()],
            batch_size=1,
            verbose=False,
        )
        result.to_directory(
            "runs/arcs-structured",
            eval_metrics_in_summary=["simple_ex", "executable", "found_one"],
        )
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
