import argparse
import os
import shutil
import json
from tqdm import trange
import collections
import time
import math
from smolagents import LiteLLMModel
from smolagents.models import get_clean_message_list
from concurrent.futures import ThreadPoolExecutor
from rattq.utils import (
    load_nl2q_samples,
    parse_query,
    is_null_result,
    get_llm_api_cost,
    save_aggregated_inference_metrics,
)
from rattq.db_connector import get_db_connectors
from rattq.baseline.nl2q_tool_agent import AGENT_MAPPINGS
from rattq.metric import bird_sql_ex

# import litellm
# litellm._turn_on_debug()


def rejection_sampling(
    agent,
    prompt: str,
    llm: str,
    db_connector,
    metric_fn,
    gold_query,
    max_tries: int = 1,
):
    t0 = time.time()
    input_tokens, output_tokens = 0, 0
    query = None
    trajectories = []
    accuracy = 0.0
    i = 0
    while i < max_tries:
        i += 1
        response = agent.run(prompt, reset=True)
        pred_query = parse_query(response)
        token_counts = agent.monitor.get_total_token_counts()
        input_tokens += int(token_counts["input"])
        output_tokens += int(token_counts["output"])
        if metric_fn(pred_query, gold_query, db_connector) == 1.0:
            query = pred_query
            trajectories.append(
                get_clean_message_list(
                    agent.write_memory_to_messages(),
                    flatten_messages_as_text=True,
                    role_conversions={
                        "tool-call": "assistant",
                        "tool-response": "user",
                    },
                )
            )
            accuracy = 1.0
            break

    metrics = {
        "latency": time.time() - t0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "api_cost_usd": get_llm_api_cost(llm, input_tokens, output_tokens),
        "success": accuracy,
        "num_tries_to_success": i if accuracy == 1.0 else math.nan,
    }
    return query, metrics, trajectories


METRIC_FN_MAPPINGS = {
    "bird-sql": bird_sql_ex,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="v1", choices=["v1"])
    parser.add_argument("--max_tries", default=1, type=int)
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
                "bird-sql_dev_1",
                # "bird-sql_dev_2",
                # "bird-sql_dev_10",
                # "bird-sql_dev_15",
            )
        ]

    model = LiteLLMModel(
        model_id=args.llm, temperature=args.temperature, **litellm_kwargs
    )

    agent_fn, prompt_fn = AGENT_MAPPINGS[args.agent]
    metric_fn = METRIC_FN_MAPPINGS[args.dataset]
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
                    rejection_sampling,
                    agent,
                    prompt,
                    args.llm,
                    db_connectors[item.db],
                    metric_fn,
                    item.gold_query,
                    args.max_tries,
                )
                for agent, prompt, item in zip(agents, prompts, batch_samples)
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

    output_path = os.path.join(args.result_dir, f"trajectories.json")
    with open(output_path, "w") as fout:
        json.dump(all_trajectories, fout, indent=2)
    print(f"Saved trajectories to {output_path}")

    save_aggregated_inference_metrics([item.metrics for item in res], args.result_dir)


if __name__ == "__main__":
    main()
