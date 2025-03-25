import argparse
import os
import shutil
import json
from tqdm import trange
import litellm
import time
import collections
from concurrent.futures import ThreadPoolExecutor
from rattq.utils import (
    load_nl2q_samples,
    parse_query,
    is_null_result,
    get_llm_api_cost,
    save_aggregated_inference_metrics,
)
from rattq.db_connector import get_db_connectors

NL2Q_PROMPT = """
Translate the following natural language question into a {language} query.
- The query must follow the database schema.
- You must use the hints to generate the query.
- You must use the 【Foreign keys】 section in the database schema to connect the tables.
- Output the query only, without any additional explanation.
- Do not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, do not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, do not fetch the score.
  - Example:
    Table: student
    [
    (id:TEXT, Primary Key, Example: 1),
    (name:TEXT, Examples: [John]),
    (score:INTEGER, Examples: [100, 95, 90]),
    ]
    Question: What is the highest score?
    Query: SELECT MAX(score) FROM student

    Question: What is the student with the highest score?
    Query: SELECT name FROM student WHERE score = (SELECT MAX(score) FROM student)

=== Your task ===

Database Schema:
{schema}

Question: {question}

Hints:
{evidence}

Query:
""".strip()


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
            sorted(set(result), key=lambda row: tuple((x is None, x) for x in row))
        )
        result2query[hashable].append(query)

    if not result2query:
        return candidates[0]

    # select majority query group
    majority_query_group = max(result2query.values(), key=len)

    # select the query with the least run time
    return min(majority_query_group, key=lambda x: run_time[x])


def run_llm(
    db_connector,
    llm: str,
    prompt: str,
    temperature: float = 0.0,
    num_candidates: int = 1,
    litellm_kwargs: dict = {},
):
    t0 = time.time()
    response = litellm.batch_completion(
        model=llm,
        messages=[[{"role": "user", "content": prompt}] for _ in range(num_candidates)],
        temperature=temperature,
        **litellm_kwargs,
    )
    queries = [r["choices"][0]["message"]["content"] for r in response]
    queries = [parse_query(q) for q in queries]
    input_tokens = sum([r["usage"]["prompt_tokens"] for r in response])
    output_tokens = sum([r["usage"]["completion_tokens"] for r in response])
    api_cost_usd = get_llm_api_cost(llm, input_tokens, output_tokens)
    latency = time.time() - t0
    metrics = {
        "latency": round(latency, 1),
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "api_cost_usd": api_cost_usd,
    }
    best_query = select_best_query(queries, db_connector)
    return best_query, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", default="openai/gpt-4o")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("-n", "--num_majority_voting_candidates", default=1, type=int)
    parser.add_argument("--prompt", default="default", choices=["default"])
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev_99")
    parser.add_argument("--batch_size", default=50, type=int)
    parser.add_argument("--wait_time_between_batches", default=0.0, type=float)
    parser.add_argument("--result_dir", default="output/nl2q_simple_zero_shot_gpt-4o/")
    parser.add_argument("--vllm_config", default="local_llm_config.json")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(batch_size=1, overwrite=True, result_dir="output/test/", split="dev")
    args = parser.parse_args()
    print(args)
    print()

    if get_llm_api_cost(args.llm, 1000000, 1000000) == 0.0:
        print(f"Warning: LLM {args.llm} is not supported for API cost calculation.")

    litellm_kwargs = {}
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
        args.dataset, splits=[args.split.split("_")[0] if "_" in args.split else args.split]
    )
    print(f"Loaded {len(db_connectors)} databases from {args.dataset} dev set.")

    dev_samples = load_nl2q_samples(args.dataset, args.split)
    print(f"Loaded {len(dev_samples)} samples from {args.dataset} dev set.")

    if args.debug:
        dev_samples = dev_samples[:3]

    res = []
    for i in trange(0, len(dev_samples), args.batch_size):
        j = min(i + args.batch_size, len(dev_samples))
        batch_samples = dev_samples[i:j]
        prompts = [
            NL2Q_PROMPT.format(
                language=item.language,
                schema=db_connectors[item.db].get_schema(),
                evidence=item.evidence,
                question=item.question,
            )
            for item in batch_samples
        ]
        if i == 0:
            print(f"<prompt>{prompts[0]}</prompt>")

        with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
            futures = [
                executor.submit(
                    run_llm,
                    db_connectors[item.db],
                    args.llm,
                    prompt,
                    args.temperature,
                    args.num_majority_voting_candidates,
                    litellm_kwargs,
                )
                for item, prompt in zip(batch_samples, prompts)
            ]
            raw_responses = [future.result() for future in futures]

        if i == 0:
            print(f"<response>{raw_responses[0][0]}</response>")

        for item, r in zip(batch_samples, raw_responses):
            query, metrics = r
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
