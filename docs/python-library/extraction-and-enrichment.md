# Extraction and enrichment

Turn long documents into typed records and add useful fields to database rows with LLMs.

## Example: Find jobs that fit

Extract work arrangements and experience requirements from saved job descriptions,
then find remote roles that require at most three years of experience:

```python title="data_enrichment.py"
--8<-- "examples/data_enrichment.py:example"
```

??? example-output no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-enrichment.txt"
    ```

Rows are processed concurrently, and both fields are written back using
`key_columns`. The output columns must already exist. Behind the scenes,
TabulaFlow uses their types and native enum choices to define and validate
each subagent's structured output for you. Enum discovery depends on the
database driver; `CHECK` constraints are not interpreted.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/data_enrichment.py
```

Already have a DataFrame? [DataFrameEnricher](api/agents.md#dataframe-enrichment)
adds typed columns directly, using the same row execution and validation.

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
df = pd.DataFrame([place.model_dump() for place in places])
assert df["category"].dropna().isin(["food", "culture", "outdoors", "shopping"]).all()
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
