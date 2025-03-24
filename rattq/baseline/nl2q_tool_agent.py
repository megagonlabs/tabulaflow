import argparse
import os
import shutil
import json
from tqdm import trange
import litellm
import time
from smolagents import ToolCallingAgent, LiteLLMModel, CodeAgent
from concurrent.futures import ThreadPoolExecutor
from smolagents.tools import tool
from sql_metadata import Parser
from smolagents.monitoring import LogLevel
from rattq.utils import (
    load_nl2q_samples,
    parse_query,
    truncate_content,
    is_null_result,
    avg_and_round,
)
from rattq.db_connector import get_db_connectors
from rattq.schema import NL2QSample

NL2Q_PROMPT = """
Translate the following natural language question into a {language} query.
- The query must follow the database schema.
- You must use the hints to generate the query.
- The final answer must be the query rather than the result of the query.
- To connect multiple tables, you must use JOIN on one of the pairs in the 【Foreign keys】 section in the database schema.
- When submitting the final query, remove any additional columns that are not required by the question.
  - If there are multiple columns that cover similar information, only include the one that is the most relevant and precise.
    - For example, if the question asks for only the list of events, only include the event ids without the dates.
    - For example, if the question asks for only the country and there are city, country, location, zipcode columns, only include the country column.
  - For example, if the question only ask for the highest score but not the name of the student, do not include the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not his score, do not include the score.
  - Example:
    Table: student
    [
    (id:TEXT, Primary Key, Example: 1),
    (name:TEXT, Examples: [John]),
    (readScore:INTEGER, Examples: [100, 95, 90]),
    (writeScore:INTEGER, Examples: [100, 95, 90]),
    (streetAddress:TEXT, Examples: ["123 Main St", "456 Maple Ave"]),
    (city:TEXT, Examples: ["Anytown", "Anycity"]),
    ]
    Question: What is the highest score in reading?
    Query: SELECT MAX(readScore) FROM student
    Question: What is the student with the highest score in reading?
    Query: SELECT name FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
    Question: What is the address of the student with the highest score in reading?
    Query: SELECT streetAddress FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
- DO NOT decompose the question into sub-questions, and use the intermediate results of previous queries to construct the final query
  - All logic of previous queries for sub-questions must be included in the final query.
  - However, you can debug a query by testing smaller components.
  - THIS IS NOT ALLOWED:
    * Question: What is the writing score of the student with the highest reading score?
    * Query 1: SELECT MAX(readScore) FROM student
    * Observation 1: 97
    * Final Query (NOT ALLOWED): SELECT writeScore FROM student WHERE readScore = 97
    The correct query should be: SELECT writeScore FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
- For non-digit text columns, always use the `search_keywords` tool to search for the keyword and ensure it exists in the database.
  - Try to search over all possible relevant columns across the database. Try to be very comprehensive.
  - Similarly, include potential synonyms in the keyword list.
- Before submitting the final query as answer, always use the `check_final_answer` tool to validate the query.

=== Your Task ===

Database Schema:
{schema}

Question: {question}

Hints:
{evidence}

{language} Query:
""".strip()


MAX_RESPONSE_LENGTH_CHARS = 1000
MAX_SEARCH_RESULTS_PER_COLUMN = 10


def get_smolagent_tools(db_connector, question: str, evidence: str):
    question = question.strip()
    evidence = evidence.strip()

    def _format_table(result: list[tuple]) -> str:
        res = "\n".join([str(row) for row in result])
        return truncate_content(res, MAX_RESPONSE_LENGTH_CHARS)

    @tool
    def check_final_answer(query: str) -> str:
        """
        Validate the final query before submission. Always use this tool to validate the query before submission.

        Args:
            query: The query to check.
        """
        result = db_connector.run_query(query)
        result_str = _format_table(result)
        if not result:
            result_str = "EMPTY RESULT"
        res = f"The query returns the following results:\n{result_str}"

        res += f'\nReminder - The original question is: "{question}"'
        if evidence:
            res += f'\nReminder - The evidence is: "{evidence}". Did you use all the evidence in the query?'
        res += f"\nReminder - You are not allowed to use intermediate results of previous queries to construct the final query. Did you include all the logic of previous queries in the final query?"

        errors = []
        if not result:
            errors.append("The query returns an empty result, the query IS INCORRECT.")
        elif is_null_result(result):
            errors.append("At least one column is all null, the query IS INCORRECT.")

        warnings = []
        if len(result) == 1 and len(result[0]) == 1 and result[0][0] == 0:
            warnings.append(
                "The query returns a single value of 0, the query might be incorrect."
            )

        # tables = Parser(query).tables
        # if len(tables) > 1 and "JOIN" not in query:
        #     warnings.append(
        #         "The query references multiple tables, but no JOIN operation is found."
        #     )

        if result and len(result[0]) > 1:
            warnings.append(
                (
                    f"Your query returns multiple columns, please check if the question asks for all these columns and remove those that are not asked for."
                    " If there are multiple columns that cover similar information, only include the one that is the most relevant and precise."
                    " For example, if the question asks for only the list of events, only include the event ids without the dates."
                    " For example, if the question asks for only the country and there are city, country, location, zipcode columns, only include the country column."
                    " For example, if the question only ask for the highest score but not the name of the student, do not include the name of the student."
                    " Similarly, if the question only ask for the student with the highest score but not his score, do not include the score."
                )
            )

        if errors:
            res += "\n\n" + "\n".join(
                [f"Error {i+1}: {e}" for i, e in enumerate(errors)]
            )

        if warnings:
            res += "\n\n" + "\n".join(
                [f"Warning {i+1}: {w}" for i, w in enumerate(warnings)]
            )

        res += f"\n\nYour query receives {len(errors)} errors and {len(warnings)} warnings."
        if errors:
            res += " Please fix the errors and submit the query again. Feel free to use any tools you want. When you are ready to submit again, call the `check_final_answer` tool again to check the query."
        else:
            res += " If you think the reminders and warnings are incorrect, you can ignore them and submit the query."
            res += " Otherwise, please try to fix the query. Feel free to use any tools you want. When you are ready to submit again, call the `check_final_answer` tool again to check the query."

        return res

    @tool
    def query_db(query: str) -> str:
        """
        Query the database with the given SQL query.

        Args:
            query: The SQL query to execute.
        """
        result = db_connector.run_query(query)
        if not result:
            return "QUERY RESULT IS EMPTY, THE QUERY IS INCORRECT"

        res = _format_table(result)
        if is_null_result(result):
            res += "\nONE OF THE COLUMNS IS ALL NULL, THE QUERY IS INCORRECT"
        return res

    @tool
    def search_keywords(table_columns: list[str], keywords: list[str]) -> str:
        """
        Fuzzy search for a keyword in the database, case-insensitive. Always use this tool to ensure a value exists in the database.

        Args:
            table_columns: A list of columns in the format of "table.column", e.g. student.`Student Name`.
            keywords: A list of keywords to search for.
        """
        res = ""
        for table_column in table_columns:
            table, column = table_column.split(".", 1)
            column = column.strip("`").strip('"')
            matches = []
            try:
                # Check if the table exists
                query = f'SELECT name FROM sqlite_master WHERE type="table" AND name="{table}"'
                result = db_connector.run_query(query)
                table_exist = len(result) > 0
                if not table_exist:
                    raise Exception(f"table {table} does not exist")

                # Check if the column exists in the table
                query = f'PRAGMA table_info("{table}")'
                result = db_connector.run_query(
                    query
                )  # This will return a list of tuples
                column_exist = any(row[1] == column for row in result)
                if not column_exist:
                    raise Exception(f"column {column} does not exist in table {table}")

                for keyword in keywords:
                    query = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" LIKE ?'
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

    return [query_db, search_keywords, check_final_answer]


def run_agent(agent, prompt: str):
    t0 = time.time()
    response = agent.run(prompt)
    latency = time.time() - t0
    token_counts = agent.monitor.get_total_token_counts()
    metrics = {
        "latency": round(latency, 1),
        "input_tokens": int(token_counts["input"]),
        "output_tokens": int(token_counts["output"]),
    }
    return response, metrics


def save_aggregated_metrics(res: list[NL2QSample], result_dir: str):
    aggregated_metrics = {
        "latency": avg_and_round([item.metrics["latency"] for item in res], 1),
        "avg_input_tokens": avg_and_round(
            [item.metrics["input_tokens"] for item in res], 2
        ),
        "avg_output_tokens": avg_and_round(
            [item.metrics["output_tokens"] for item in res], 2
        ),
        "total_input_tokens": sum([item.metrics["input_tokens"] for item in res]),
        "total_output_tokens": sum([item.metrics["output_tokens"] for item in res]),
    }

    output_path = os.path.join(result_dir, f"aggregated_metrics.json")
    with open(output_path, "w") as fout:
        json.dump(aggregated_metrics, fout, indent=2)
    print(f"Saved aggregated metrics to {output_path}")


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

    if args.debug:
        verbosity = LogLevel.INFO
    else:
        verbosity = LogLevel.ERROR

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

        agents = [
            ToolCallingAgent(
                tools=get_smolagent_tools(
                    db_connectors[sample.db], sample.question, sample.evidence
                ),
                model=model,
                verbosity_level=verbosity,
            )
            for sample in batch_samples
        ]

        with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
            futures = [
                executor.submit(run_agent, agent, prompt)
                for agent, prompt in zip(agents, prompts)
            ]
            raw_responses = [future.result() for future in futures]

        if i == 0:
            # print(
            #     f"<last_agent_step_input>{agents[-1].memory.steps[-1].model_input_messages}</last_agent_step_input>"
            # )
            # print(
            #     f"<last_agent_step_output>{agents[-1].memory.steps[-1].model_output_message}</last_agent_step_output>"
            # )
            print(f"<response>{raw_responses[0][0]}</response>")

        for item, r in zip(batch_samples, raw_responses):
            query, metrics = r
            item.pred_query = parse_query(query)
            item.metrics.update(metrics)
            res.append(item)

    output_path = os.path.join(args.result_dir, f"result.json")
    with open(output_path, "w") as fout:
        json.dump([item.model_dump(mode="json") for item in res], fout, indent=2)
    print(f"Saved result to {output_path}")

    save_aggregated_metrics(res, args.result_dir)


if __name__ == "__main__":
    main()
