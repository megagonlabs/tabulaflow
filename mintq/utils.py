import json
import math
import os
import litellm
import random
from mintq.schema import NL2QTask, SingleOutputNL2QTask, MultiOutputNL2QTask, Trajectory


def parse_json(response: str):
    lines = response.strip().split("\n")
    if lines[0].startswith("```") and lines[-1].startswith("```"):
        response = "\n".join(lines[1:-1])
    return json.loads(response)


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
        res[key] = avg_and_round([m[key] for m in all_metrics if not math.isnan(m[key])], 2)
        if key in ("input_tokens", "output_tokens", "api_cost_usd"):
            res[f"total_{key}"] = sum([m[key] for m in all_metrics if not math.isnan(m[key])])

    output_path = os.path.join(result_dir, f"aggregated_metrics.json")
    with open(output_path, "w") as fout:
        json.dump(res, fout, indent=2)
    print(f"Saved aggregated metrics to {output_path}")


def get_trajectory_num_steps(trajectory: list[dict]) -> int:
    return len([msg for msg in trajectory["messages"] if msg["role"].lower() == "assistant"])


def split_train_dev(samples: list[dict], ratio: float = 0.9) -> tuple[list[dict], list[dict]]:
    sampler = random.Random(42)
    train_indices = sampler.sample(range(len(samples)), int(len(samples) * ratio))
    train_samples = [samples[i] for i in train_indices]
    dev_samples = [samples[i] for i in range(len(samples)) if i not in set(train_indices)]
    return train_samples, dev_samples


def load_nl2q_tasks(path: str) -> list[NL2QTask]:
    with open(path, "r") as f:
        data = json.load(f)
    for cls in (SingleOutputNL2QTask, MultiOutputNL2QTask):
        try:
            return [cls(**item) for item in data]
        except Exception:
            continue
    raise ValueError(f"No valid NL2QTask found in {path}")


def save_results(results: list[NL2QTask], result_dir: str):
    if not isinstance(results[0], SingleOutputNL2QTask):
        raise ValueError("Only single-output NL2Q tasks are supported currently")

    with open(os.path.join(result_dir, "result.json"), "w") as f:
        json.dump([task.model_dump(mode="json") for task in results], f, indent=2)

    if "sql" in results[0].language.lower():
        extension = "sql"
    elif results[0].language.lower() == "cypher":
        extension = "cypher"
    else:
        extension = "txt"

    gold_query_dir = os.path.join(result_dir, "gold_query")
    os.makedirs(gold_query_dir, exist_ok=True)
    for task in results:
        with open(os.path.join(gold_query_dir, f"{task.qid}.{extension}"), "w") as f:
            f.write("\n\n".join(task.gold_queries) + "\n")

    pred_query_dir = os.path.join(result_dir, "pred_query")
    os.makedirs(pred_query_dir, exist_ok=True)
    for task in results:
        with open(os.path.join(pred_query_dir, f"{task.qid}.{extension}"), "w") as f:
            f.write(task.pred_query + "\n")

    trajectory_dir = os.path.join(result_dir, "trajectory")
    os.makedirs(trajectory_dir, exist_ok=True)
    for task in results:
        with open(os.path.join(trajectory_dir, f"{task.qid}.txt"), "w") as f:
            f.write(pprint_trajectory(task.trajectory) + "\n")

    print(f"Saved results to {result_dir}")


def pprint_trajectory(trajectory: Trajectory) -> str:
    res = []
    for msg in trajectory.messages:
        if msg.role == "system":
            res.append(f"<message role=system>\n{msg.content}\n</message>")
        elif msg.role == "user":
            res.append(f"<message role=user>\n{msg.content}\n</message>")
        elif msg.role == "assistant":
            s = f"<message role=assistant>\n<content>{msg.content}</content>\n"
            for tool_call in msg.tool_calls:
                s += f"<function={tool_call.name}>\n"
                for key, value in tool_call.arguments.items():
                    s += f"<parameter={key}>"
                    s += f"\n{value}\n" if "\n" in value else value
                    s += "</parameter>\n"
                s += "</function>\n"
            s += "</message>"
            res.append(s)
        elif msg.role == "tool":
            res.append(f"<message role=tool>\n{msg.response}\n</message>")
    return "\n\n".join(res)
