import json
import math
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

