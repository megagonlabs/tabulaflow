# Extraction and enrichment

Use LLMs to extract typed records from long documents and add fields to existing rows.
Both extraction and enrichment support text, images, and PDFs.

## Example: Find jobs that fit

Add work arrangement and experience requirements to saved job listings:

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

Build a list of places to visit from a [sample travel guide](../examples/support/travel_guide.txt),
with a category and a short reason for each recommendation. The script loads the guide automatically:

```python title="document_extraction.py"
--8<-- "examples/document_extraction.py:example"
```

??? example-output no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-extraction.txt"
    ```

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/document_extraction.py
```

The extractor also accepts images and PDFs as `BinaryContent` with a model
that supports those inputs. See the
[extraction reference](api/agents.md#extraction-and-summarization).
