import argparse
import os
import shutil
import json
from tqdm import trange
import collections
import time
import math
from dataclasses import dataclass
from typing import List
import smolagents
from smolagents.memory import MemoryStep, Message
from smolagents import LiteLLMModel
from smolagents.models import ChatMessage, MessageRole
import litellm
from concurrent.futures import ThreadPoolExecutor
from rattq.utils import (
    load_nl2q_samples,
    parse_query,
    get_trajectory_num_steps,
    get_llm_api_cost,
    save_aggregated_inference_metrics,
)
from rattq.db_connector import get_db_connectors
from rattq.baseline.nl2q_tool_agent import AGENT_MAPPINGS
from rattq.metric import bird_sql_ex
from rattq.patch_smolagents import smolagents_use_tool_format

# import litellm
# litellm._turn_on_debug()


def rejection_sampling(
    agent,
    task: str,
    db_connector,
    metric_fn,
    gold_query,
    max_tries: int = 1,
    max_steps: int = 20,
    verbose: bool = False,
):
    t0 = time.time()
    query = None
    trajectories = []
    num_tries = 0
    while num_tries < max_tries:
        num_tries += 1
        pred_query = agent.run_new_task(
            task, max_steps=max_steps, allow_max_steps_reached=False
        )
        if pred_query and metric_fn(pred_query, gold_query, db_connector) == 1.0:
            query = pred_query
            trajectories.append(agent.get_trajectory())
            break

    metrics = agent.get_metrics()
    metrics["latency"] = time.time() - t0
    metrics["success"] = 1 if query else 0
    metrics["num_tries_to_success"] = num_tries if query else math.nan
    metrics["trajectory_steps"] = (
        get_trajectory_num_steps(trajectories[0]) if query else math.nan
    )
    return query, metrics, trajectories


FEEDBACK_PROMPT = """
A student agent tried to accomplish a task but it got stuck. You are a teacher who needs to provide a guide to help the student agent.

### His Task:
{task}

### Here are the actions he has tried so far:
{history}

### Your instructions:
You have access to the gold query: {gold_query}
However, you should never reveal it to the your student directly.
Instead, you should provide concise one-paragraph suggestions or plans that will help the student come up with the gold query himself.
Address the student as "you" in your feedback.
- First, summarize what the student has done so far in a few sentences. If the student's current answer does not align with the question, explain briefly why it is wrong.
- Next, provide the suggestions for future actions.
  - Your suggestions should always be based on the task instruction, schema, question, hints, available tools, and what hasn't been tried in the action history.
  - Your suggestions should NOT be based on the gold query. For example, you should not provide the column names and values in the gold query directly.
""".strip()


def rejection_sampling_with_teacher_feedback(
    agent,
    task: str,
    db_connector,
    metric_fn,
    gold_query,
    max_tries: int = 1,
    max_steps: int = 20,
    feedback_temperature: float = 0.7,
    verbose: bool = False,
):
    t0 = time.time()
    query = None
    trajectories = []
    num_tries = 0
    while num_tries < max_tries:
        num_tries += 1
        pred_query = agent.run_new_task(
            task, max_steps=max_steps, allow_max_steps_reached=False
        )
        success = pred_query and metric_fn(pred_query, gold_query, db_connector) == 1.0
        if not success:
            # remove the final_answer step or max-step-reached step
            agent.remove_last_k_actions(1)
            # consider at most the first 8 actions (the first step is the task step)
            agent.truncate_to_first_k_actions(8)
            messages = agent.get_trajectory()["messages"]
            # skip the system message and the task message
            messages = messages[2:]
            history = json.dumps(messages, indent=2)

            feedback_prompt = FEEDBACK_PROMPT.format(
                task=task, history=history, gold_query=gold_query
            )
            if verbose:
                print(f"<feedback_prompt>{feedback_prompt}</feedback_prompt>")
            feedback = litellm.completion(
                model=agent.get_llm_name(),
                messages=[{"role": "user", "content": feedback_prompt}],
                temperature=feedback_temperature,
            )["choices"][0]["message"]["content"].strip()
            if verbose:
                verbose = False
                print(f"<feedback>{feedback}</feedback>")

            curr_steps = get_trajectory_num_steps(agent.get_trajectory())
            agent.add_feedback(feedback)
            remaining_steps = max_steps - curr_steps
            pred_query = agent.continue_task(
                max_steps=remaining_steps, allow_max_steps_reached=False
            )
            agent.remove_all_feedback()
            success = (
                pred_query and metric_fn(pred_query, gold_query, db_connector) == 1.0
            )
        if success:
            query = pred_query
            trajectories.append(agent.get_trajectory())
            break

    metrics = agent.get_metrics()
    metrics["latency"] = time.time() - t0
    metrics["success"] = 1 if query else 0
    metrics["num_tries_to_success"] = num_tries if query else math.nan
    metrics["trajectory_steps"] = (
        get_trajectory_num_steps(trajectories[0]) if query else math.nan
    )
    return query, metrics, trajectories


METRIC_FN_MAPPINGS = {
    "bird-sql": bird_sql_ex,
}

SAMPLE_FN_MAPPINGS = {
    "rejection": rejection_sampling,
    "teacher_feedback": rejection_sampling_with_teacher_feedback,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="v1", choices=["v1"])
    parser.add_argument(
        "--sampling",
        default="teacher_feedback",
        choices=["rejection", "teacher_feedback"],
    )
    parser.add_argument("--max_tries", default=1, type=int)
    parser.add_argument("--use_tool_format", action="store_true")
    parser.add_argument("--llm", default="openai/gpt-4o")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="train_64")
    parser.add_argument("--batch_size", default=50, type=int)
    parser.add_argument("--result_dir", default="output/nl2q_tool_agent_gpt-4o/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--vllm_config", default="local_llm_config.json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(
            batch_size=1,
            overwrite=True,
            result_dir="output/test_trajectories/",
            split="dev",
        )
    args = parser.parse_args()
    print(args)
    print()

    if args.use_tool_format:
        smolagents_use_tool_format()

    if get_llm_api_cost(args.llm, 1000000, 1000000) == 0.0:
        print(f"Warning: LLM {args.llm} is not supported for API cost calculation.")

    litellm_kwargs = {"tool_choice": "auto"}
    if args.llm.startswith("hosted_vllm/"):
        with open(args.vllm_config, "r") as f:
            litellm_kwargs["api_base"] = json.load(f)[args.llm]["api_base"]

    if os.path.exists(args.result_dir):
        if not args.overwrite:
            print(
                f"{args.result_dir} already exists. Use --overwrite to overwrite the directory."
            )
            return
        else:
            shutil.rmtree(args.result_dir)
    os.makedirs(args.result_dir)

    db_connectors = get_db_connectors(
        args.dataset,
        splits=[args.split.split("_")[0] if "_" in args.split else args.split],
    )
    print(
        f"Loaded {len(db_connectors)} databases from {args.dataset} {args.split} set."
    )

    nl2q_samples = load_nl2q_samples(args.dataset, args.split)
    print(f"Loaded {len(nl2q_samples)} samples from {args.dataset} {args.split} set.")

    if args.debug and args.split == "dev":
        nl2q_samples = [
            item
            for item in nl2q_samples
            if item.qid
            in (
                # "bird-sql_dev_1",
                # "bird-sql_dev_2",
                "bird-sql_dev_10",
                # "bird-sql_dev_15",
            )
        ]

    model = LiteLLMModel(
        model_id=args.llm, temperature=args.temperature, **litellm_kwargs
    )

    agent_fn, prompt_fn = AGENT_MAPPINGS[args.agent]
    metric_fn = METRIC_FN_MAPPINGS[args.dataset]
    sampling_fn = SAMPLE_FN_MAPPINGS[args.sampling]

    res = []
    all_trajectories = []
    for i in trange(0, len(nl2q_samples), args.batch_size):
        j = min(i + args.batch_size, len(nl2q_samples))
        batch_samples = nl2q_samples[i:j]
        prompts = [prompt_fn(db_connectors[item.db], item) for item in batch_samples]
        if i == 0:
            print(f"<prompts>{prompts[0]}</prompts>")

        agents = [
            agent_fn(db_connectors[item.db], item, model, verbose=args.debug)
            for item in batch_samples
        ]

        with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
            futures = [
                executor.submit(
                    sampling_fn,
                    agent,
                    prompt,
                    db_connectors[item.db],
                    metric_fn,
                    item.gold_query,
                    args.max_tries,
                    verbose=i == 0 and k == 0,
                )
                for k, (agent, prompt, item) in enumerate(
                    zip(agents, prompts, batch_samples)
                )
            ]
            raw_responses = [future.result() for future in futures]

        if i == 0:
            # print(f"<last_agent_step_input>{agents[-1].memory.steps[-1].model_input_messages}</last_agent_step_input>")
            # print(f"<last_agent_step_output>{agents[-1].memory.steps[-1].model_output_message}</last_agent_step_output>")
            print(f"<response>{raw_responses[0][0]}</response>")

        for item, r in zip(batch_samples, raw_responses):
            query, metrics, trajectories = r
            item.pred_query = query
            item.metrics.update(metrics)
            res.append(item)
            all_trajectories += trajectories

    output_path = os.path.join(args.result_dir, f"result.json")
    with open(output_path, "w") as fout:
        json.dump([item.model_dump(mode="json") for item in res], fout, indent=2)
    print(f"Saved result to {output_path}")

    output_path = os.path.join(args.result_dir, f"trajectories.jsonl")
    with open(output_path, "w") as fout:
        for trajectory in all_trajectories:
            fout.write(json.dumps(trajectory) + "\n")
    print(f"Saved trajectories to {output_path}")

    save_aggregated_inference_metrics([item.metrics for item in res], args.result_dir)


if __name__ == "__main__":
    main()
