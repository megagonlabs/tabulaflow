import json
import math
import os
import re
import pandas as pd
import litellm
from mintq.schema import Trajectory, NL2QRunResult


def extract_code(response: str) -> str:
    m = re.search(r"```(?:([\w+-]+))?\n([\s\S]*?)\n```", response)
    if m:
        return m.group(2).strip()
    else:
        return response.strip()


def avg_and_round(nums: list[float], n: int = 4) -> float:
    return round(sum(nums) / len(nums), n) if nums else math.nan


def get_llm_api_cost(llm: str, input_tokens: int, output_tokens: int) -> float:
    try:
        input_cost, output_cost = litellm.cost_per_token(  # type: ignore
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


def save_csv(result: NL2QRunResult, path: str, metrics_to_include: list[str] = []) -> None:
    headers = ["qid", "db", "question", "evidence", "gold_query", "pred_query"] + metrics_to_include
    data = []

    for task in result.tasks:
        if task.task_type != "simple":
            raise ValueError("Only simple NL2Q tasks are supported currently")

        data.append(
            (task.qid, task.db, task.question, task.evidence, "\n\n".join(task.gold_queries), task.pred_query)
            + tuple(task.metrics[m] for m in metrics_to_include)
        )

    df = pd.DataFrame(data, columns=headers)
    df.to_csv(path, index=False)


def save_results(result: NL2QRunResult, result_dir: str) -> None:
    os.makedirs(result_dir, exist_ok=True)

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
    pred_query_dir = os.path.join(result_dir, "pred_query")
    trajectory_dir = os.path.join(result_dir, "trajectory")

    os.makedirs(gold_query_dir, exist_ok=True)
    os.makedirs(pred_query_dir, exist_ok=True)
    os.makedirs(trajectory_dir, exist_ok=True)

    for task in result.tasks:
        if task.task_type != "simple":
            raise ValueError("Only simple NL2Q tasks are supported currently")

        with open(os.path.join(gold_query_dir, f"{task.qid}.{extension}"), "w") as f:
            f.write("\n\n".join(task.gold_queries))

        with open(os.path.join(pred_query_dir, f"{task.qid}.{extension}"), "w") as f:
            f.write(task.pred_query)

        with open(os.path.join(trajectory_dir, f"{task.qid}.xml"), "w") as f:
            f.write(format_trajectory(task.trajectory))
            f.write("\n\n\n" + "\n\n".join(f"<gold_query>\n{g}\n</gold_query>" for g in task.gold_queries))

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
                try:
                    content = json.loads(msg.content)
                    content = json.dumps(content, indent=2)
                except Exception:
                    content = msg.content
                s += f"{content}\n"
            for tool_call in msg.tool_calls:
                s += f'<function name="{tool_call.name}">\n'
                for key, value in tool_call.arguments.items():
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value, indent=2)
                    else:
                        value = str(value)
                    s += f'<arg name="{key}">'
                    s += f"\n{value}\n" if "\n" in value else value
                    s += "</arg>\n"
                s += "</function>\n"
            s += "</message>"
            res.append(s)
        elif msg.role == "tool":
            res.append(f'<message role="tool">\n{msg.response}\n</message>')
    return "<trajectory>\n" + "\n\n\n".join(res) + "\n</trajectory>"
