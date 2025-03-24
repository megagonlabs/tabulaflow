import json
import math
import os
from rattq.schema import NL2QSample


def load_nl2q_samples(dataset_name: str, split: str) -> list[NL2QSample]:
    if dataset_name == "bird-sql":
        dir_name = "dev_20240627" if split == "dev" else split
        with open(f"data/BIRD-SQL/{dir_name}/{split}.json", "r") as f:
            data = json.load(f)
        return [
            NL2QSample(
                qid=f"{dataset_name}_{split}_{i}",
                language="SQLite",
                db=item["db_id"],
                question=item["question"],
                evidence=item["evidence"],
                gold_query=item["SQL"],
            )
            for i, item in enumerate(data)
        ]
    else:
        raise ValueError(f"Dataset {dataset_name} not supported")


def parse_query(response) -> str:
    if isinstance(response, dict):
        if "query" in response:
            response = response["query"]
        elif "answer" in response:
            response = response["answer"]

    if isinstance(response, str):
        lines = response.strip().split("\n")
        if lines[0].startswith("```") and lines[-1].startswith("```"):
            response = "\n".join(lines[1:-1])
        return response
    else:
        return ""


def truncate_content(content: str, max_length_chars: int = 1000) -> str:
    # borrowed from https://github.com/huggingface/smolagents/blob/main/src/smolagents/utils.py
    if len(content) <= max_length_chars:
        return content
    else:
        return (
            content[: max_length_chars // 2]
            + f"\n..._This content has been truncated to stay below {max_length_chars} characters_...\n"
            + content[-max_length_chars // 2 :]
        )


def is_null_result(result: list[tuple]) -> bool:
    if not result:  # empty result
        return True

    # Check if any column is all None
    n_cols = len(result[0])
    for i in range(n_cols):
        if all(row[i] is None for row in result):
            return True
    return False


def avg_and_round(nums: list[float], n: int = 4):
    return round(sum(nums) / len(nums), n) if nums else math.nan


LLM_API_COST_PER_MILLION_TOKENS = {
    "openai/gpt-4o": (2.5, 10),
    "openai/gpt-4o-mini": (0.15, 0.6),
}


def get_llm_api_cost(llm: str, input_tokens: int, output_tokens: int) -> float:
    if llm not in LLM_API_COST_PER_MILLION_TOKENS:
        return 0.0

    input_cost, output_cost = LLM_API_COST_PER_MILLION_TOKENS[llm]
    total_cost = (input_tokens / 1000000) * input_cost + (
        output_tokens / 1000000
    ) * output_cost
    return round(total_cost, 2)


def save_aggregated_inference_metrics(all_metrics: list[dict], result_dir: str):
    aggregated_metrics = {
        "latency": avg_and_round([metrics["latency"] for metrics in all_metrics], 1),
        "avg_input_tokens": avg_and_round(
            [metrics["input_tokens"] for metrics in all_metrics], 2
        ),
        "avg_output_tokens": avg_and_round(
            [metrics["output_tokens"] for metrics in all_metrics], 2
        ),
        "total_input_tokens": sum([metrics["input_tokens"] for metrics in all_metrics]),
        "total_output_tokens": sum(
            [metrics["output_tokens"] for metrics in all_metrics]
        ),
        "avg_api_cost_usd": avg_and_round(
            [metrics["api_cost_usd"] for metrics in all_metrics], 2
        ),
        "total_api_cost_usd": sum([metrics["api_cost_usd"] for metrics in all_metrics]),
    }

    output_path = os.path.join(result_dir, f"aggregated_metrics.json")
    with open(output_path, "w") as fout:
        json.dump(aggregated_metrics, fout, indent=2)
    print(f"Saved aggregated metrics to {output_path}")
