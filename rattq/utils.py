import json
import math
import os
import litellm
import random
from rattq.schema import NL2QSample


def load_nl2q_samples(dataset_name: str, split: str) -> list[NL2QSample]:
    if dataset_name == "bird-sql":
        sample_size = None
        if "_" in split:
            split, sample_size = split.split("_")

        if split == "dev":
            dir_name = "dev_20240627"
        elif split == "train":
            dir_name = "train"
        else:
            raise ValueError(f"Split {split} not supported")

        with open(f"data/BIRD-SQL/{dir_name}/{split}.json", "r") as f:
            data = json.load(f)

        data = [
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

        if sample_size:
            sampler = random.Random(42)
            data = sampler.sample(data, int(sample_size))

        return data
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


def get_llm_api_cost(llm: str, input_tokens: int, output_tokens: int) -> float:
    try:
        input_cost, output_cost = litellm.cost_per_token(
            model=llm, prompt_tokens=input_tokens, completion_tokens=output_tokens
        )
        return round(input_cost + output_cost, 2)
    except:
        return 0.0


def save_aggregated_inference_metrics(all_metrics: list[dict], result_dir: str):
    res = {}
    keys = list(all_metrics[0].keys())
    for key in keys:
        res[key] = avg_and_round([m[key] for m in all_metrics], 2)
        if key in ("input_tokens", "output_tokens", "api_cost_usd"):
            res[f"total_{key}"] = sum([m[key] for m in all_metrics])

    output_path = os.path.join(result_dir, f"aggregated_metrics.json")
    with open(output_path, "w") as fout:
        json.dump(res, fout, indent=2)
    print(f"Saved aggregated metrics to {output_path}")
