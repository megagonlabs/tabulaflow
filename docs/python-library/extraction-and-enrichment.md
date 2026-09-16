# Extraction and enrichment

Use LLMs to extract typed records from long documents and add fields to existing rows.
Both extraction and enrichment support text, images, and PDFs.

## Example: Find jobs that fit

Add work arrangement and experience fields to saved jobs, then find remote roles
that require at most three years of experience:

```python title="data_enrichment.py"
--8<-- "examples/data_enrichment.py:example"
```

??? example-output no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-enrichment.txt"
    ```

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/data_enrichment.py
```

For enrichment that needs external information,
[`RunSubagentForEachRowTool`](api/agents.md#extraction-and-enrichment-tools)
can give each row's agent browser and database tools, then write the results
back to the table automatically.

## Extract records from documents

Build a list of places to visit from a travel guide, with a category and a short
reason for each recommendation. Save the [sample guide](../examples/support/travel_guide.txt)
as `travel_guide.txt`:

```python
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel

from tabulaflow.agents.extraction import EntityExtractor


class Place(BaseModel):
    name: str
    city: str
    category: Literal["food", "culture", "outdoors", "shopping"]
    why_visit: str


guide = Path("travel_guide.txt").read_text(encoding="utf-8")
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
```

??? example-output no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-extraction.txt"
    ```

The extractor splits long documents into chunks and processes them concurrently.
It also accepts images and PDFs as `BinaryContent` with a model that supports
those inputs. See the
[extraction reference](api/agents.md#extraction-and-summarization).
