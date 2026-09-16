# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3", "pydantic>=2.12", "httpx>=0.28.1"]
# ///

# --8<-- [start:example]
import asyncio
from typing import Literal

import httpx
import pandas as pd
from pydantic import BaseModel

from tabulaflow.agents.extraction import EntityExtractor


class Place(BaseModel):
    name: str
    city: str
    category: Literal["food", "culture", "outdoors", "shopping"]
    why_visit: str


async def main() -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://megagonlabs.github.io/tabulaflow/examples/support/travel_guide.txt")
        response.raise_for_status()
    guide = response.text

    extractor = EntityExtractor(llm="openai-responses:gpt-5-mini")
    # Long documents are split into chunks and processed concurrently.
    # Results are combined into one list of validated Place instances.
    places = await extractor.extract(
        guide,
        record_type=Place,
        instruction=(
            "Extract one record per recommended place. Use the city from its section. "
            "Choose the category that best fits the main reason to visit, and summarize "
            "that reason in at most eight words. Skip background mentions and travel logistics."
        ),
    )
    assert all(place.category in {"food", "culture", "outdoors", "shopping"} for place in places)
    df = pd.DataFrame([place.model_dump() for place in places])
    print(df.to_string(index=False))


if __name__ == "__main__":
    asyncio.run(main())
# --8<-- [end:example]
