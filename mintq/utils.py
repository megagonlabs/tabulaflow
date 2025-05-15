import json
import math
import os
import litellm
import random
from mintq.schema import Trajectory, NL2QRunResult


def parse_json(response: str):
    lines = response.strip().split("\n")
    if lines[0].startswith("```") and lines[-1].startswith("```"):
        response = "\n".join(lines[1:-1])
    return json.loads(response)


def parse_query(response: str) -> str:
    lines = response.strip().split("\n")
    if lines[0].startswith("```") and lines[-1].startswith("```"):
        response = "\n".join(lines[1:-1])
    return response


def avg_and_round(nums: list[float], n: int = 4):
    return round(sum(nums) / len(nums), n) if nums else math.nan


def get_llm_api_cost(llm: str, input_tokens: int, output_tokens: int) -> float:
    try:
        input_cost, output_cost = litellm.cost_per_token(
            model=llm, prompt_tokens=input_tokens, completion_tokens=output_tokens
        )
        return round(input_cost + output_cost, 2)
    except Exception:
        return 0.0


def get_aggregated_metrics(all_metrics: list[dict[str, float | int]]) -> dict[str, float | int]:
    res = {}
    keys = list(all_metrics[0].keys())
    for key in keys:
        res[f"avg_{key}"] = avg_and_round([m[key] for m in all_metrics if not math.isnan(m[key])], 4)
        if key in ("input_tokens", "output_tokens", "api_cost_usd"):
            res[f"total_{key}"] = sum([m[key] for m in all_metrics if not math.isnan(m[key])])
    return res


def get_trajectory_num_steps(trajectory: list[dict]) -> int:
    return len([msg for msg in trajectory["messages"] if msg["role"].lower() == "assistant"])


def split_train_dev(samples: list[dict], ratio: float = 0.9) -> tuple[list[dict], list[dict]]:
    sampler = random.Random(42)
    train_indices = sampler.sample(range(len(samples)), int(len(samples) * ratio))
    train_samples = [samples[i] for i in train_indices]
    dev_samples = [samples[i] for i in range(len(samples)) if i not in set(train_indices)]
    return train_samples, dev_samples


def save_results(result: NL2QRunResult, result_dir: str) -> None:
    if result.tasks[0].task_type != "single_output":
        raise ValueError("Only single-output NL2Q tasks are supported currently")

    with open(os.path.join(result_dir, "result.json"), "w") as f:
        f.write(result.model_dump_json(indent=2))

    language = result.tasks[0].language.lower()
    if language.startswith("sql") or language.endswith("sql"):
        extension = "sql"
    elif language == "cypher":
        extension = "cypher"
    else:
        extension = "query"

    gold_query_dir = os.path.join(result_dir, "gold_query")
    os.makedirs(gold_query_dir, exist_ok=True)
    for task in result.tasks:
        with open(os.path.join(gold_query_dir, f"{task.qid}.{extension}"), "w") as f:
            f.write("\n\n".join(task.gold_queries) + "\n")

    pred_query_dir = os.path.join(result_dir, "pred_query")
    os.makedirs(pred_query_dir, exist_ok=True)
    for task in result.tasks:
        with open(os.path.join(pred_query_dir, f"{task.qid}.{extension}"), "w") as f:
            f.write(task.pred_query + "\n")

    trajectory_dir = os.path.join(result_dir, "trajectory")
    os.makedirs(trajectory_dir, exist_ok=True)
    for task in result.tasks:
        if task.trajectory:
            with open(os.path.join(trajectory_dir, f"{task.qid}.xml"), "w") as f:
                f.write(pprint_trajectory(task.trajectory) + "\n")

    print(f"Saved results to {result_dir}")


def pprint_trajectory(trajectory: Trajectory) -> str:
    res = []
    for msg in trajectory.messages:
        if msg.role == "system":
            res.append(f'<message role="system">\n{msg.content}\n</message>')
        elif msg.role == "user":
            res.append(f'<message role="user">\n{msg.content}\n</message>')
        elif msg.role == "assistant":
            s = f'<message role="assistant">\n<content>{msg.content}</content>\n'
            for tool_call in msg.tool_calls:
                s += f'<function name="{tool_call.name}">\n'
                for key, value in tool_call.arguments.items():
                    s += f'<parameter name="{key}">'
                    s += f"\n{value}\n" if "\n" in value else value
                    s += "</parameter>\n"
                s += "</function>\n"
            s += "</message>"
            res.append(s)
        elif msg.role == "tool":
            res.append(f'<message role="tool">\n{msg.response}\n</message>')
    return "\n\n\n".join(res)
