# Extraction and enrichment

Use LLMs to extract typed records from long documents and add fields to existing rows.
Both extraction and enrichment support text, images, and PDFs.

## Example: Find jobs that fit

You're comparing job listings across industries. Extract the business domain,
work arrangement, and experience requirements into typed columns so you can
filter the roles.

```python title="data_enrichment.py"
--8<-- "examples/data_enrichment.py:example"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-enrichment.txt"
    ```

Behind the scenes, TabulaFlow runs a subagent for each row in parallel. Each run
returns structured output validated against `JobDetails`, which TabulaFlow turns
into new DataFrame columns.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/data_enrichment.py
```

For enrichment that needs web information, enable browser tools directly:

```python
enricher = DataFrameEnricher(enable_browser_tools=True)
```

Each row agent gets its own browser tools, which are closed when the row finishes
or is cancelled. To query registered data sources, pass a `DataConnectorRegistry`
as `registry` and set `enable_run_query_tool=True`.

For enrichment that writes results back to a database table,
[`RunSubagentForEachRowTool`](api/agents.md#extraction-and-enrichment-tools)
uses the same row execution runtime and writes each result as it completes.
Its nested-subagent option enables multiple levels of task decomposition.
Individual row failures are recorded while other rows continue.

## Extract records from documents

Build a list of places to visit from a [sample travel guide](../examples/support/travel_guide.txt),
with a category and a short reason for each recommendation. The script loads the guide automatically:

```python title="document_extraction.py"
--8<-- "examples/document_extraction.py:example"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-extraction.txt"
    ```

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/document_extraction.py
```

The extractor splits long text at natural boundaries where possible, keeping
paragraphs, list items, and table rows together. Section titles and table headers
carry across chunks, helping each subagent interpret records in context
(e.g., which city a place belongs to).

You can also extract records from images and PDFs with a compatible model.
PDF chunks include their original page ranges. See the
[extraction reference](api/agents.md#extraction-and-summarization).
