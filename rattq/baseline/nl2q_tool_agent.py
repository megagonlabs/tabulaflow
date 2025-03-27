import argparse
import os
import shutil
import json
from tqdm import trange
import collections
import time
from smolagents import LiteLLMModel
from concurrent.futures import ThreadPoolExecutor
from rattq.utils import (
    load_nl2q_samples,
    parse_query,
    is_null_result,
    get_llm_api_cost,
    save_aggregated_inference_metrics,
)
from rattq.db_connector import get_db_connectors
from rattq.baseline.agent_v1 import get_agent_v1, get_prompt_v1
from rattq.patch_smolagents import smolagents_use_tool_format

# import litellm
# litellm._turn_on_debug()


def select_best_query(candidates, db_connector):
    result2query = collections.defaultdict(list)
    run_time = {}
    for query in candidates:
        t0 = time.time()
        try:
            result = db_connector.run_query(query)
            if is_null_result(result):
                continue
        except Exception as e:
            continue
        run_time[query] = time.time() - t0
        hashable = tuple(
            sorted(set(result), key=lambda row: tuple((x is None, str(type(x)), x) for x in row))
        )
        result2query[hashable].append(query)

    if not result2query:
        return candidates[0]

    # select majority query group
    majority_query_group = max(result2query.values(), key=len)

    # select the query with the least run time
    return min(majority_query_group, key=lambda x: run_time[x])


def run_agent(
    agent, prompt: str, llm: str, db_connector, num_majority_voting_candidates: int = 1
):
    t0 = time.time()
    input_tokens, output_tokens = 0, 0
    queries = []
    trajectory_steps = []
    trajectories = []
    for _ in range(num_majority_voting_candidates):
        response = agent.run(prompt, reset=True)
        queries.append(parse_query(response))
        token_counts = agent.monitor.get_total_token_counts()
        input_tokens += int(token_counts["input"])
        output_tokens += int(token_counts["output"])
        trajectory_steps.append(agent.memory.steps[-1].step_number)
        trajectories.append(agent.write_memory_to_messages())

    best_query = select_best_query(queries, db_connector)
    best_index = queries.index(best_query)

    metrics = {
        "latency": round(time.time() - t0, 1),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "api_cost_usd": get_llm_api_cost(llm, input_tokens, output_tokens),
        "trajectory_steps": trajectory_steps[best_index],
    }
    trajectory = trajectories[best_index]
    return response, metrics, trajectory


AGENT_MAPPINGS = {
    "v1": (get_agent_v1, get_prompt_v1),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="v1", choices=["v1"])
    parser.add_argument("--llm", default="openai/gpt-4o")
    parser.add_argument("--use_tool_format", action="store_true")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("-n", "--num_majority_voting_candidates", default=1, type=int)
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev_199")
    parser.add_argument("--batch_size", default=50, type=int)
    parser.add_argument("--result_dir", default="output/nl2q_tool_agent_gpt-4o/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--vllm_config", default="local_llm_config.json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(
            batch_size=1, overwrite=True, result_dir="output/test/", split="dev"
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
    print(f"Loaded {len(db_connectors)} databases from {args.dataset} dev set.")

    dev_samples = load_nl2q_samples(args.dataset, args.split)
    print(f"Loaded {len(dev_samples)} samples from {args.dataset} dev set.")

    if args.debug:
        dev_samples = [
            item
            for item in dev_samples
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

    res = []
    trajectories = []
    for i in trange(0, len(dev_samples), args.batch_size):
        j = min(i + args.batch_size, len(dev_samples))
        batch_samples = dev_samples[i:j]
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
                    run_agent,
                    agent,
                    prompt,
                    args.llm,
                    db_connectors[item.db],
                    args.num_majority_voting_candidates,
                )
                for agent, prompt, item in zip(agents, prompts, batch_samples)
            ]
            raw_responses = [future.result() for future in futures]

        if i == 0:
            # print(f"<last_agent_step_input>{agents[-1].memory.steps[-1].model_input_messages}</last_agent_step_input>")
            # print(f"<last_agent_step_output>{agents[-1].memory.steps[-1].model_output_message}</last_agent_step_output>")
            print(f"<response>{raw_responses[0][0]}</response>")

        for item, r in zip(batch_samples, raw_responses):
            query, metrics, trajectory = r
            item.pred_query = query
            item.metrics.update(metrics)
            res.append(item)
            trajectories.append({"qid": item.qid, "trajectory": trajectory})

    output_path = os.path.join(args.result_dir, f"result.json")
    with open(output_path, "w") as fout:
        json.dump([item.model_dump(mode="json") for item in res], fout, indent=2)
    print(f"Saved result to {output_path}")

    output_path = os.path.join(args.result_dir, f"trajectories.json")
    with open(output_path, "w") as fout:
        json.dump(trajectories, fout, indent=2)
    print(f"Saved trajectories to {output_path}")

    save_aggregated_inference_metrics([item.metrics for item in res], args.result_dir)


if __name__ == "__main__":
    main()
