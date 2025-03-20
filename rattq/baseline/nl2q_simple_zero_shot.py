import argparse
import os
import shutil
import json
from tqdm import trange
import litellm
import time
import collections
from rattq.utils import load_nl2q_samples, parse_query
from rattq.db_connector import get_db_connectors

NL2Q_PROMPT = """
Translate the following natural language question into a {language} query.
- The query must follow the database schema.
- You must use the hints to generate the query.
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


def is_null_result(result):
    if not result:  # empty result
        return True

    # Check if any column is all None
    n_cols = len(result[0])
    for i in range(n_cols):
        if all(row[i] is None for row in result):
            return True
    return False


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", default="openai/gpt-4o")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("-n", "--num_majority_voting_candidates", default=1, type=int)
    parser.add_argument("--prompt", default="default", choices=["default"])
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--batch_size", default=50, type=int)
    parser.add_argument("--wait_time_between_batches", default=0.0, type=float)
    parser.add_argument("--result_dir", default="output/nl2q_simple_zero_shot_gpt-4o/")
    parser.add_argument("--vllm_config", default="local_llm_config.json")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(batch_size=1, overwrite=True, result_dir="output/test/")
    args = parser.parse_args()
    print(args)
    print()

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

    db_connectors = get_db_connectors(args.dataset, splits=["dev"])
    print(f"Loaded {len(db_connectors)} databases from {args.dataset} dev set.")

    dev_samples = load_nl2q_samples(args.dataset, "dev")
    print(f"Loaded {len(dev_samples)} samples from {args.dataset} dev set.")

    if args.debug:
        dev_samples = dev_samples[:3]

    res = []
    for i in trange(0, len(dev_samples), args.batch_size):
        j = min(i + args.batch_size, len(dev_samples))
        batch_samples = dev_samples[i:j]
        prompts = []
        for sample in batch_samples:
            prompts += [
                NL2Q_PROMPT.format(
                    language=sample.language,
                    schema=db_connectors[sample.db].get_schema(),
                    evidence=sample.evidence,
                    question=sample.question,
                )
            ] * args.num_majority_voting_candidates

        if i == 0:
            print(f"<prompt>{prompts[0]}</prompt>")

        responses = litellm.batch_completion(
            model=args.llm,
            messages=[[{"role": "user", "content": s}] for s in prompts],
            temperature=args.temperature,
            **litellm_kwargs,
        )
        assert (
            len(responses) == len(batch_samples) * args.num_majority_voting_candidates
        )
        responses = [r["choices"][0]["message"]["content"] for r in responses]
        responses = [parse_query(r) for r in responses]
        if i == 0:
            print(f"<response>{responses[0]}</response>")

        for k, sample in enumerate(batch_samples):
            candidates = responses[k : k + args.num_majority_voting_candidates]
            sample.pred_query = select_best_query(candidates, db_connectors[sample.db])
            res.append(sample)

    output_path = os.path.join(args.result_dir, f"result.json")
    with open(output_path, "w") as fout:
        json.dump([item.model_dump(mode="json") for item in res], fout, indent=2)
    print(f"Saved result to {output_path}")


if __name__ == "__main__":
    main()
