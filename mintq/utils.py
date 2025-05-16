import math
import os
import litellm
from mintq.schema import Trajectory, NL2QRunResult


def extract_code(response: str) -> str:
    response = response.strip()
    lines = response.split("\n")
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
        return input_cost + output_cost
    except Exception:
        return 0.0


def get_aggregated_metrics(all_metrics: list[dict[str, float | int]]) -> dict[str, float | int]:
    res = {}
    keys = list(all_metrics[0].keys())
    for key in keys:
        res[f"avg_{key}"] = avg_and_round([m[key] for m in all_metrics if not math.isnan(m[key])], 4)
        if key in ("api_calls", "input_tokens", "output_tokens", "api_cost_usd"):
            summ = sum([m[key] for m in all_metrics if not math.isnan(m[key])])
            res[f"total_{key}"] = round(summ, 4) if isinstance(summ, float) else summ
    return res


def save_str_list(strings: list[str], filenames: list[str], directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    for s, filename in zip(strings, filenames):
        with open(os.path.join(directory, filename), "w") as f:
            f.write(s)


def save_results(result: NL2QRunResult, result_dir: str) -> None:
    if result.tasks[0].task_type != "simple":
        raise ValueError("Only simple NL2Q tasks are supported currently")

    with open(os.path.join(result_dir, "result.json"), "w") as f:
        f.write(result.model_dump_json(indent=2))

    language = result.tasks[0].language.lower()
    if language.startswith("sql") or language.endswith("sql"):
        extension = "sql"
    elif language == "cypher":
        extension = "cypher"
    else:
        extension = "query"

    save_str_list(
        ["\n\n".join(task.gold_queries) for task in result.tasks],
        [f"{task.qid}.{extension}" for task in result.tasks],
        os.path.join(result_dir, "gold_query"),
    )

    save_str_list(
        [task.pred_query for task in result.tasks],
        [f"{task.qid}.{extension}" for task in result.tasks],
        os.path.join(result_dir, "pred_query"),
    )

    save_str_list(
        [format_trajectory(task.trajectory) + "\n" for task in result.tasks],
        [f"{task.qid}.xml" for task in result.tasks],
        os.path.join(result_dir, "trajectory"),
    )

    print(f"Saved results to {result_dir}")


def format_trajectory(trajectory: Trajectory) -> str:
    res = []
    for msg in trajectory.messages:
        if msg.role == "system":
            res.append(f'<message role="system">\n{msg.content}\n</message>')
        elif msg.role == "user":
            res.append(f'<message role="user">\n{msg.content}\n</message>')
        elif msg.role == "assistant":
            s = '<message role="assistant">\n'
            if msg.content:
                s += f"{msg.content}\n"
            for tool_call in msg.tool_calls:
                s += f'<function name="{tool_call.name}">\n'
                for key, value in tool_call.arguments.items():
                    s += f'<arg name="{key}">'
                    s += f"\n{value}\n" if "\n" in value else value
                    s += "</arg>\n"
                s += "</function>\n"
            s += "</message>"
            res.append(s)
        elif msg.role == "tool":
            res.append(f'<message role="tool">\n{msg.response}\n</message>')
    return "\n\n\n".join(res)
