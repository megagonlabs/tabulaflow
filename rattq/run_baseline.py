import argparse
import os
import shutil
import json
from tqdm import trange
from concurrent.futures import ThreadPoolExecutor
from rattq.utils import *
from rattq.db_connector import get_db_connectors
from rattq.schema_formatter import get_schema_formatter
from rattq.baseline import get_nl2q_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline",
        default="simple_zero_shot",
        choices=["simple_zero_shot", "tool_agent"],
    )
    parser.add_argument("-s", "--schema_formatter", default="sql_default")
    parser.add_argument("--llm", default="openai/gpt-4o")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("-n", "--num_majority_voting_candidates", default=1, type=int)
    parser.add_argument("--local_llm_config", default="local_llm_config.json")

    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="199")

    parser.add_argument("--batch_size", default=50, type=int)
    parser.add_argument("--result_dir", default="output/nl2q_simple_zero_shot_gpt-4o/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(
            batch_size=1, overwrite=True, result_dir="output/test/", split="dev"
        )
    args = parser.parse_args()
    print(args)
    print()

    if os.path.exists(args.result_dir):
        if not args.overwrite:
            print(
                f"{args.result_dir} already exists. Use --overwrite to overwrite the directory."
            )
            return
        else:
            shutil.rmtree(args.result_dir)
    os.makedirs(args.result_dir)

    if get_llm_api_cost(args.llm, 1000000, 1000000) == 0.0:
        print(f"Warning: LLM {args.llm} is not supported for API cost calculation.")

    litellm_kwargs = {}
    if args.llm.startswith("hosted_vllm/"):
        with open(args.local_llm_config, "r") as f:
            litellm_kwargs["api_base"] = json.load(f)[args.llm]["api_base"]
    schema_formatter = get_schema_formatter(args.schema_formatter)
    nl2q_kwargs = {
        "llm": args.llm,
        "temperature": args.temperature,
        "num_candidates": args.num_majority_voting_candidates,
        "litellm_kwargs": litellm_kwargs,
        "schema_formatter": schema_formatter,
    }

    db_connectors = get_db_connectors(args.dataset, splits=[args.split])
    print(f"Loaded {len(db_connectors)} databases from {args.dataset} dev set.")

    samples = load_nl2q_samples(args.dataset, args.split)
    print(f"Loaded {len(samples)} samples from {args.dataset} dev set.")

    if args.debug:
        samples = samples[:3]

    res = []
    for i in trange(0, len(samples), args.batch_size):
        j = min(i + args.batch_size, len(samples))
        batch = samples[i:j]

        nl2q_models = [get_nl2q_model(args.baseline, **nl2q_kwargs) for _ in batch]

        with ThreadPoolExecutor(max_workers=len(batch)) as executor:
            futures = [
                executor.submit(
                    nl2q_model.predict,
                    item,
                    db_connectors[item.db],
                )
                for item, nl2q_model in zip(batch, nl2q_models)
            ]
            raw_responses = [future.result() for future in futures]

        if i == 0:
            print(f"<trajectory>{json.dumps(raw_responses[0][1], indent=2)}</trajectory>")

        for item, r in zip(batch, raw_responses):
            query, trajectory, metrics = r
            item.pred_query = query
            item.metrics.update(metrics)
            res.append(item)

    output_path = os.path.join(args.result_dir, f"result.json")
    with open(output_path, "w") as fout:
        json.dump([item.model_dump(mode="json") for item in res], fout, indent=2)
    print(f"Saved result to {output_path}")

    save_aggregated_inference_metrics([item.metrics for item in res], args.result_dir)


if __name__ == "__main__":
    main()
