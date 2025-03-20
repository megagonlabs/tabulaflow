import argparse
import os
import shutil
import json
from tqdm import trange
import litellm
from smolagents import ToolCallingAgent, LiteLLMModel, CodeAgent
from concurrent.futures import ThreadPoolExecutor
from smolagents.tools import tool
from rattq.utils import load_nl2q_samples, parse_query, truncate_content
from rattq.db_connector import get_db_connectors


NL2Q_PROMPT = """
Translate the following natural language question into a {language} query.
- The query must follow the database schema.
- You must use the hints to generate the query.
- The final answer must be the query rather than the result of the query.
- Do not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, do not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, do not fetch the score.
- For non-digit text columns, always use the `search_keyword` tool to search for the keyword and ensure it exists in the database.
  - Try to search over all potentially relevant columns in the database, and include potential synonyms in the keyword list.
- Before submitting the final query as answer, always execute the query to validate it.
  - The execution result should be non-empty and reasonable (not null, not zero, etc.)

Database Schema:
{schema}

Question: {question}

Hints:
{evidence}

Query:
""".strip()


MAX_RESPONSE_LENGTH_CHARS = 1000
MAX_SEARCH_RESULTS_PER_COLUMN = 10


def get_smolagent_tools(db_connector):

    @tool
    def query_db(query: str) -> str:
        """
        Query the database with the given SQL query.

        Args:
            query: The SQL query to execute.
        """
        result = db_connector.run_query(query)
        if not result:
            return "QUERY RESULT IS EMPTY"

        res = "\n".join([str(row) for row in result])
        res = truncate_content(res, MAX_RESPONSE_LENGTH_CHARS)
        return res

    @tool
    def search_keyword(table_columns: list[str], keywords: list[str]) -> str:
        """
        Fuzzy search for a keyword in the database, case-insensitive.

        Args:
            table_columns: A list of columns in the format of "table.column", e.g. student."Student Name".
            keywords: A list of keywords to search for.
        """
        res = ""
        for table_column in table_columns:
            table, column = table_column.split(".", 1)
            if " " in column and column[0] != '"':
                column = f'"{column}"'
            matches = []
            try:
                for keyword in keywords:
                    query = (
                        f'SELECT DISTINCT {column} FROM "{table}" WHERE {column} LIKE ?'
                    )
                    result = db_connector.run_query(query, (f"%{keyword}%",))
                    matches += [row[0] for row in result]
                matches = sorted(list(set(matches)))
                if len(matches) > MAX_SEARCH_RESULTS_PER_COLUMN:
                    matches_str = (
                        json.dumps(matches[:MAX_SEARCH_RESULTS_PER_COLUMN]) + ", ..."
                    )
                else:
                    matches_str = json.dumps(matches)
                res += f"[{table}.{column}] {len(matches)} matches: {matches_str}\n"
            except Exception as e:
                res += f"[{table}.{column}] ERROR ENCOUNTERED: {str(e)}\n"

        return res

    return [query_db, search_keyword]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", default="openai/gpt-4o")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("--prompt", default="default", choices=["default"])
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--batch_size", default=50, type=int)
    parser.add_argument("--wait_time_between_batches", default=0.0, type=float)
    parser.add_argument("--result_dir", default="output/nl2q_tool_agent_gpt-4o/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--vllm_config", default="local_llm_config.json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(batch_size=1, overwrite=True, result_dir="output/test/")
    args = parser.parse_args()
    print(args)
    print()

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

    db_connectors = get_db_connectors(args.dataset, splits=["dev"])
    print(f"Loaded {len(db_connectors)} databases from {args.dataset} dev set.")

    dev_samples = load_nl2q_samples(args.dataset, "dev")
    print(f"Loaded {len(dev_samples)} samples from {args.dataset} dev set.")

    if args.debug:
        dev_samples = [
            sample
            for sample in dev_samples
            if sample.qid
            in (
                "bird-sql_dev_1",
                "bird-sql_dev_2",
                "bird-sql_dev_10",
                "bird-sql_dev_15",
                "bird-sql_dev_16",
            )
        ]

    model = LiteLLMModel(
        model_id=args.llm, temperature=args.temperature, **litellm_kwargs
    )

    res = []
    for i in trange(0, len(dev_samples), args.batch_size):
        j = min(i + args.batch_size, len(dev_samples))
        batch_samples = dev_samples[i:j]
        prompts = [
            NL2Q_PROMPT.format(
                language=sample.language,
                schema=db_connectors[sample.db].get_schema(),
                evidence=sample.evidence,
                question=sample.question,
            )
            for sample in batch_samples
        ]
        if i == 0:
            print(f"<prompts>{prompts[0]}</prompts>")

        responses = []
        agents = [
            ToolCallingAgent(
                tools=get_smolagent_tools(db_connectors[sample.db]), model=model
            )
            for sample in batch_samples
        ]

        with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
            futures = [
                executor.submit(agent.run, prompt)
                for agent, prompt in zip(agents, prompts)
            ]
            responses = [future.result() for future in futures]

        if i == 0:
            print(
                f"<last_agent_step_input>{agents[-1].memory.steps[-1].model_input_messages}</last_agent_step_input>"
            )
            print(
                f"<last_agent_step_output>{agents[-1].memory.steps[-1].model_output_message}</last_agent_step_output>"
            )
            print(f"<response>{responses[0]}</response>")

        for item, r in zip(batch_samples, responses):
            item.pred_query = parse_query(r)
            res.append(item)

    output_path = os.path.join(args.result_dir, f"result.json")
    with open(output_path, "w") as fout:
        json.dump([item.model_dump(mode="json") for item in res], fout, indent=2)
    print(f"Saved result to {output_path}")


if __name__ == "__main__":
    main()
