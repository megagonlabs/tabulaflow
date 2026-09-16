# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3", "pydantic>=2.12"]
# ///

# --8<-- [start:example]
import asyncio
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from tabulaflow.agents.enrichment import DataFrameEnricher


class JobDetails(BaseModel):
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None
    min_experience_years: int | None = Field(default=None, ge=0)


async def main() -> None:
    jobs = pd.DataFrame(
        {
            "title": ["Backend Engineer", "Data Analyst", "ML Engineer"],
            "description": [
                "Work from home with no office days. Requires two years building Python services.",
                "Join our London office every Tuesday and Thursday. Requires three years of SQL experience.",
                "Work from anywhere with our ML team. Requires at least five years in machine learning.",
            ],
        }
    )

    enricher = DataFrameEnricher(llm="openai-responses:gpt-5-mini")
    # Rows run concurrently, with types, categories, and constraints validated for every result.
    enriched = await enricher.enrich(
        jobs,
        record_type=JobDetails,
        instruction=(
            "Identify the work arrangement and minimum years of experience required. "
            "Leave unstated requirements null. Job description: {{ description }}"
        ),
    )
    assert all(mode in {"remote", "hybrid", "onsite"} for mode in enriched["work_mode"].dropna())

    matches = enriched.loc[
        (enriched["work_mode"] == "remote") & (enriched["min_experience_years"] <= 3),
        ["title", "work_mode", "min_experience_years"],
    ]
    print(matches.to_string(index=False))


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
