# Extraction and enrichment

Extract typed records from documents and enrich database rows with LLMs.

## Example: Classify support tickets

Select uncategorized tickets with SQL, classify each row concurrently, and
write the results back to the table:

```python title="data_enrichment.py"
--8<-- "examples/data_enrichment.py:example"
```

??? example-output no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-enrichment.txt"
    ```

`key_columns` identify the rows to update. The output columns must already
exist. Behind the scenes, TabulaFlow uses their types and native enum choices
to define and validate each subagent's structured output for you. Enum discovery
depends on the database driver; `CHECK` constraints are not interpreted.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/data_enrichment.py
```

## Extract records from documents

Use `EntityExtractor` directly when the input is a document:

```python
from tabulaflow.agents.extraction import EntityExtractor

extractor = EntityExtractor(
    {"product": str, "price_usd": float},
    llm="openai-responses:gpt-5-mini",
)
records = await extractor.extract(
    "USB-C dock: $89. Laptop stand: $45.",
    instruction="Extract each product and its price in USD.",
)
print(records)
```

??? example-output no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-extraction.txt"
    ```

The extractor chunks long documents automatically. It also accepts images and
PDFs as `BinaryContent` with a model that supports those inputs. See the
[extraction reference](api/agents.md#extraction-and-summarization).
