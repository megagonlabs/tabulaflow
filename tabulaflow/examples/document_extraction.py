# --8<-- [start:example]
import asyncio
from importlib.resources import files
from typing import Literal

import pandas as pd
from pydantic import BaseModel

from tabulaflow.agents.extraction import EntityExtractor


class Place(BaseModel):
    name: str
    city: str
    category: Literal["food", "culture", "outdoors", "shopping"]
    why_visit: str


async def main() -> None:
    guide = files("tabulaflow.examples.support").joinpath("travel_guide.txt").read_text()

    extractor = EntityExtractor(llm="openai:gpt-5-mini")
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
