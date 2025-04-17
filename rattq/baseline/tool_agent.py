import json
import yaml
import importlib
import smolagents
from smolagents.monitoring import LogLevel
from rattq.utils import truncate_content, is_null_result
from rattq.schema import NL2QTask
from rattq.schema_formatter import BaseSchemaFormatter
from rattq.baseline.base import SmolagentsNL2QAgent
from rattq.db_connector import BaseDBConnector


NL2Q_PROMPT_V1 = """
Translate the following natural language question into a {language} query.
- The query must follow the database schema.
- You must use the hints to generate the query.
- The final answer must be the query rather than the result of the query.
- To connect multiple tables, you must use JOIN on one of the pairs in the 【Foreign keys】 section in the database schema.
  -  Keep in mind that the records in the tables may not perfectly align: the some entities in one table might not be covered by another table.
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


MAX_RESPONSE_LENGTH_CHARS = 250
MAX_SEARCH_RESULTS_PER_COLUMN = 10


def get_smolagent_tools_v1(db_connector, question: str, evidence: str):
    question = question.strip()
    evidence = evidence.strip()

    def _format_table(result: list[tuple]) -> str:
        res = "\n".join([str(row) for row in result])
        return truncate_content(res, MAX_RESPONSE_LENGTH_CHARS)

    @smolagents.tools.tool
    def check_final_answer(query: str) -> str:
        """
        Validate the final query before submission. Always use this tool to validate the query before submission.

        Args:
            query: The query to check.
        """
        res = ""
        result = None
        errors = []
        warnings = []
        try:
            result = db_connector.run_query(query)
            result_str = _format_table(result)
            if not result:
                result_str = "EMPTY RESULT"
            res += f"The query returns the following results:\n{result_str}"
        except Exception as e:
            errors.append(f"Query execution failed: {str(e)}")

        res += f'\nReminder - The original question is: "{question}"'
        if evidence:
            res += f'\nReminder - The evidence is: "{evidence}". Did you use all the evidence in the query?'
        res += f"\nReminder - You are not allowed to use intermediate results of previous queries to construct the final query. Did you include all the logic of previous queries in the final query?"

        if result is not None:
            if not result:
                errors.append(
                    "The query returns an empty result, the query IS INCORRECT."
                )
            elif result and is_null_result(result):
                errors.append(
                    "At least one column is all null, the query IS INCORRECT."
                )
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

    @smolagents.tools.tool
    def query_db(query: str) -> str:
        """
        Query the database with the given SQL query.

        Args:
            query: The SQL query to execute.
        """
        try:
            result = db_connector.run_query(query)
        except Exception as e:
            return f"Query execution failed: {str(e)}"

        if not result:
            return "QUERY RESULT IS EMPTY, THE QUERY IS INCORRECT"

        res = _format_table(result)
        if is_null_result(result):
            res += "\nONE OF THE COLUMNS IS ALL NULL, THE QUERY IS INCORRECT"
        return res

    @smolagents.tools.tool
    def search_keywords(table_columns: list[str], keywords: list[str]) -> str:
        """
        Fuzzy search for a keyword in the database, case-insensitive. Always use this tool to ensure a value exists in the database.

        Args:
            table_columns: A list of columns in the format of "table.column", e.g. student."Student Name".
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


class ToolAgentNL2Q(SmolagentsNL2QAgent):
    def __init__(
        self,
        llm: str,
        schema_formatter: BaseSchemaFormatter,
        temperature: float = 0.0,
        num_candidates: int = 1,
        litellm_kwargs: dict = {},
        verbose: bool = False,
    ):
        if num_candidates > 1:
            raise ValueError("num_candidates > 1 is not supported yet")

        self.llm = llm
        self.schema_formatter = schema_formatter
        self.temperature = temperature
        self.num_candidates = num_candidates
        self.litellm_kwargs = litellm_kwargs
        self.verbose = verbose

    def format_prompt(self, task: NL2QTask, db_connector: BaseDBConnector) -> str:
        return NL2Q_PROMPT_V1.format(
            language=task.language,
            schema=db_connector.schema,
            evidence=task.evidence,
            question=task.question,
        )

    def get_smolagent(
        self, task: NL2QTask, db_connector: BaseDBConnector
    ) -> smolagents.MultiStepAgent:
        prompt_templates = yaml.safe_load(
            importlib.resources.files("smolagents.prompts")
            .joinpath("toolcalling_agent.yaml")
            .read_text()
        )

        model = smolagents.LiteLLMModel(
            model_id=self.llm, temperature=self.temperature, **self.litellm_kwargs
        )

        prompt_templates["system_prompt"] = "You are a helpful database expert."
        return smolagents.ToolCallingAgent(
            prompt_templates=prompt_templates,
            tools=get_smolagent_tools_v1(db_connector, task.question, task.evidence),
            model=model,
            verbosity_level=LogLevel.INFO if self.verbose else LogLevel.ERROR,
            max_steps=20,
        )
