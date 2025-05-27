import asyncio
from mintq.modelhub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.datahub.bird_sql import BirdSQLDatasetLoader
from mintq.schema_formatter import SQLDefaultSchemaFormatter
from mintq.metric import BirdSQLEx
from mintq.run_model import run_model_async
from mintq.evaluate import evaluate_async


async def main():
    dataloader = BirdSQLDatasetLoader(directory="data/BIRD-SQL")
    # dataset includes the text-to-query tasks and the database connectors
    dataset = await dataloader.get_split_async("dev")  
    dataset.tasks = dataset.tasks[:3]

    # define the model arguments
    # the `run_model` function below uses this to construct a separate model instance for each sample to avoid race condition
    model_args = {"llm": "openai/gpt-4o-mini", "schema_formatter": SQLDefaultSchemaFormatter()}
    # run the model on the dataset using multi-threading
    result = await run_model_async(SimpleZeroShotNL2Q, model_args, dataset=dataset, batch_size=8)
    print(result.tasks[0].pred_query)
    # SELECT MAX("Percent (%) Eligible Free (K-12)")
    # FROM frpm
    # WHERE "County Name" = 'Alameda';

    # evaluate execution accuracy
    metrics = [BirdSQLEx()]
    result_with_metrics = await evaluate_async(result, dataset, metrics, batch_size=8)
    print(result_with_metrics.aggregated_metrics)
    # {'avg_latency_seconds': 1.472, 'avg_api_calls': 1.0, 'total_api_calls': 3, 'avg_input_tokens': 2490.6667, 'total_input_tokens': 7472, 'avg_output_tokens': 49.3333, 'total_output_tokens': 148, 'avg_api_cost_usd': 0.0004, 'total_api_cost_usd': 0.0012, 'avg_steps': 1.0, 'bird_sql_ex': 0.3333}


if __name__ == "__main__":
    asyncio.run(main())
