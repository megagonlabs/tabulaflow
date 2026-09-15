# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

# --8<-- [start:example]
import asyncio

import pandas as pd

from tabulaflow.agents.tools import RunSubagentForEachRowTool
from tabulaflow.data import SQLConnector


async def main():
    database = await SQLConnector.from_url_async("duckdb:///:memory:", read_only=False)
    result = await database.run_query_async("""
        CREATE TABLE jobs (
            job_id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            work_mode ENUM ('remote', 'hybrid', 'onsite'),
            min_experience_years INTEGER
        )
    """)
    if result.error is not None:
        raise RuntimeError(result.error.message)
    await database.write_dataframe_async(
        pd.DataFrame(
            {
                "job_id": [1, 2, 3],
                "title": ["Backend Engineer", "Data Analyst", "ML Engineer"],
                "description": [
                    "Work from home with no office days. Requires two years building Python services.",
                    "Join our London office every Tuesday and Thursday. Requires three years of SQL experience.",
                    "Work from anywhere with our ML team. Requires at least five years in machine learning.",
                ],
            }
        ),
        "jobs",
        mode="append",
    )

    enricher = RunSubagentForEachRowTool(database, subagent_llm="openai-responses:gpt-5-mini")
    # Column types and enum choices constrain each subagent's output.
    # Rows are processed concurrently and results are written back automatically.
    summary = await enricher.execute(
        schema_name=None,
        table_name="jobs",
        task_query="SELECT job_id, description FROM jobs WHERE work_mode IS NULL",
        task_instruction=(
            "Identify the work arrangement and minimum years of experience required. "
            "Leave unstated requirements null. Job description: {{ description }}"
        ),
        key_columns=["job_id"],
        output_columns=["work_mode", "min_experience_years"],
    )
    print(summary)

    result = await database.run_query_async("SELECT work_mode FROM jobs")
    assert result.error is None and result.df is not None
    assert result.df["work_mode"].dropna().isin(["remote", "hybrid", "onsite"]).all()

    result = await database.run_query_async("""
        SELECT title, work_mode, min_experience_years
        FROM jobs
        WHERE work_mode = 'remote' AND min_experience_years <= 3
        ORDER BY job_id
    """)
    if result.error is not None:
        raise RuntimeError(result.error.message)
    print(result.df.to_string(index=False))
    await database.close_async()


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
