# --8<-- [start:example]
import asyncio
from typing import Literal

import pandas as pd
from pydantic import BaseModel

from tabulaflow.agents.enrichment import DataFrameEnricher


class JobDetails(BaseModel):
    business_domain: str | None = None
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None
    min_experience_years: int | None = None


async def main() -> None:
    jobs = pd.DataFrame(
        [
            {
                "title": "Backend Engineer",
                "description": (
                    "Build payment APIs for a financial services company. Work from home with no office days. "
                    "Requires two years building Python services."
                ),
            },
            {
                "title": "Data Analyst",
                "description": (
                    "Analyze sales for a retail chain. Join our London office every Tuesday and Thursday. "
                    "Requires three years of SQL experience."
                ),
            },
            {
                "title": "ML Engineer",
                "description": (
                    "Develop diagnostic models for a healthcare provider. Work from anywhere with our ML team. "
                    "Requires at least five years in machine learning."
                ),
            },
        ]
    )

    enricher = DataFrameEnricher(llm="openai-responses:gpt-5-mini")
    enriched = await enricher.enrich(
        jobs,
        record_type=JobDetails,
        instruction=(
            "Identify the business domain, work arrangement, and minimum years of experience required. "
            "Leave unstated details null.\n"
            "Job title: {{ title }}\n"
            "Job description: {{ description }}"
        ),
    )
    assert all(mode in {"remote", "hybrid", "onsite"} for mode in enriched["work_mode"].dropna())

    print(enriched[["title", "business_domain", "work_mode", "min_experience_years"]].to_string(index=False))


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
