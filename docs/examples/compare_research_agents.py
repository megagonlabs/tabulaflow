# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

import pandas as pd

from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.research.agents import BasicAgentConfig, DirectPromptAgent
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgent, SchemaLinkingAgentConfig
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx, Executable
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async
from tabulaflow.research.types import NL2QRunResult


def summarize_runs(results: list[NL2QRunResult]) -> pd.DataFrame:
    """Compare accuracy and recorded inference usage for completed runs."""
    return pd.DataFrame(
        [
            {
                "Agent": result.agent,
                "Accuracy": result.aggregated_eval_metrics["bird_sql_ex"]["avg"],
                "Executable": result.aggregated_eval_metrics["executable"]["avg"],
                "Tokens": result.total_usage.input_tokens + result.total_usage.output_tokens
                if result.total_usage is not None
                else None,
                "Cost (USD)": result.total_usage.api_cost_usd if result.total_usage is not None else None,
                "Avg. latency (s)": result.aggregated_inference_metrics.get("latency_seconds", {}).get("avg"),
            }
            for result in results
        ]
    )


async def main() -> None:
    initialize_agent_runtime(AgentRuntimeConfig(preprocessing_cache_mode="read_write"))
    dataset = await BirdSQLDatasetLoader().get_split_async("dev", subsample_size=5)
    # --8<-- [start:strategies]
    llm = "openai-responses:gpt-5-mini"
    strategies = [
        (DirectPromptAgent, BasicAgentConfig(llm=llm)),
        (
            SchemaLinkingAgent,
            SchemaLinkingAgentConfig(llm=llm, do_schema_linking=True, do_postprocessing=True),
        ),
    ]
    # --8<-- [end:strategies]

    try:
        # --8<-- [start:comparison]
        results = []
        for agent_cls, config in strategies:
            result = await predict_async(agent_cls, config, dataset, batch_size=5)
            await execute_async(result, dataset, batch_size=5)
            await evaluate_async(result, dataset, metrics=[BirdSQLEx(), Executable()], batch_size=5)
            result.to_directory(f"runs/{result.agent}", eval_metrics_in_summary=["bird_sql_ex", "executable"])
            results.append(result)
        # --8<-- [end:comparison]

        print(summarize_runs(results).fillna("—").to_markdown(index=False, floatfmt=".3f"))
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
