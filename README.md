<h1>
  <a href="https://megagonlabs.github.io/tabulaflow/">
    <img src="https://raw.githubusercontent.com/megagonlabs/tabulaflow/main/docs/assets/tabulaflow-wordmark.svg?v=2" alt="TabulaFlow" width="240">
  </a>
</h1>

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize, or transform. It works with all kinds of data, including
SQL and graph databases, files, Hugging Face datasets, Wikidata, and web pages.

Like a general-purpose coding agent, it can also write code, work with files,
run shell commands, and browse the web.

Explore the [documentation](https://megagonlabs.github.io/tabulaflow/).



https://github.com/user-attachments/assets/ac975684-afcc-4702-a325-d015fb89665d



**More demos:**
[Find Research Papers](https://megagonlabs.github.io/tabulaflow/#demo-research) ·
[Ask Your Database Anything](https://megagonlabs.github.io/tabulaflow/#demo-database) ·
[Explore a Multimodal Hugging Face Dataset](https://megagonlabs.github.io/tabulaflow/#demo-hugging-face) ·
[Query and Visualize Graphs](https://megagonlabs.github.io/tabulaflow/#demo-wikidata)

## Get started

Install TabulaFlow with [`uv`](https://docs.astral.sh/uv/), set a model provider
key, and launch it:

```bash
uv tool install tabulaflow
export OPENAI_API_KEY="your-api-key"
tabulaflow
```

We also recommend installing Chromium to enable agent-driven web browsing:

```bash
uv tool run --from playwright playwright install chromium
```

TabulaFlow opens with bundled sample data, so you can start exploring
immediately.

## TabulaFlow as a Python Library

At the core of TabulaFlow is a minimalist, async-native Python library for building
and researching data agents. It was the first thing we built when we started this project because existing libraries
lacked the abstractions we needed. Its building blocks allow you to write agent
logic that runs across different database backends and research benchmarks. The same library
powers the [TabulaFlow data agent](https://megagonlabs.github.io/tabulaflow/).

You can use any of these building blocks to create
data applications with (e.g. data agents) or without an LLM (e.g., interactive dashboards). Choose the
building blocks you need:

- [Data connectors](https://megagonlabs.github.io/tabulaflow/python-library/data-connectors/): inspect schemas and query SQL
  databases, Neo4j, SPARQL endpoints, files, and datasets through a unified
  async interface.
- [Extraction and enrichment](https://megagonlabs.github.io/tabulaflow/python-library/extraction-and-enrichment/): turn documents
  into structured records and enrich DataFrames with new fields.
- [Chat sessions](https://megagonlabs.github.io/tabulaflow/python-library/chat-sessions/): use `ChatSession` to converse
  across multiple data sources, run tools, and stream answers and progress,
  with automatic context compaction for long conversations.
- [Structured outputs](https://megagonlabs.github.io/tabulaflow/python-library/structured-outputs/): let agents produce tables, charts, maps,
  and graphs as structured artifacts by defining declarative specifications, with optional lazy data resolution for
  parameter-driven interaction.
- [Custom agents](https://megagonlabs.github.io/tabulaflow/python-library/custom-agents/): combine reusable query, visualization, and
  document tools with your own functions and actions, without adopting `ChatSession`.
- [Schema and result formatting](https://megagonlabs.github.io/tabulaflow/python-library/api/output/#formatting): turn structured
  schemas and query results into readable text for LLM prompts or human
  inspection.

These building blocks are fully typed and organized into four layers:
`core <- data <- output <- agents`. See the
[API reference](https://megagonlabs.github.io/tabulaflow/python-library/api-reference/) for how they fit together.

### Quick start

Add TabulaFlow to your Python project:

```bash
uv add tabulaflow
```

With `OPENAI_API_KEY` set, compare sales and support data from separate
in-memory databases, then inspect the structured chart and table results:

```python
import asyncio

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector
from tabulaflow.output.specs import ChartArtifactSpec, TableArtifactSpec


async def load_sample_data(sales: SQLConnector, support: SQLConnector) -> None:
    await sales.write_dataframe_async(
        pd.DataFrame(
            columns=["order_id", "region", "revenue_usd"],
            data=[
                (1001, "West", 1200),
                (1002, "West", 800),
                (1003, "East", 900),
                (1004, "East", 600),
            ],
        ),
        "sales",
    )
    await support.write_dataframe_async(
        pd.DataFrame(
            columns=["ticket_id", "subject", "priority", "status"],
            data=[
                (201, "Checkout payment failures", "high", "open"),
                (202, "Invoice downloads unavailable", "high", "open"),
                (203, "Profile image upload issue", "low", "open"),
                (204, "Password reset emails delayed", "high", "resolved"),
            ],
        ),
        "support",
    )


async def main() -> None:
    async with DataConnectorRegistry() as registry:
        sales = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        registry.register("sales", sales)
        support = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
        registry.register("support", support)
        await load_sample_data(sales, support)

        async with ChatSession(
            registry=registry,
            model="openai:gpt-5-mini",
            reasoning="low",
        ) as session:
            result = await session.run(
                "How does revenue compare across regions, and which high-priority "
                "support tickets are still open? Show revenue as a bar chart "
                "and the tickets in a table."
            )
            print("Answer:", result.text)

            for artifact in result.output.artifacts:
                if isinstance(artifact, (TableArtifactSpec, ChartArtifactSpec)):
                    data = await session.output_store.resolve_artifact_source(artifact.source_id)
                    print("Artifact:", artifact.label)
                    print("Source:", data.metadata.connector_alias)
                    print("SQL:", data.metadata.query)
                    print("DataFrame:\n", data.df)


if __name__ == "__main__":
    asyncio.run(main())
```

`result.text` contains the answer; `result.output` contains structured artifact
specifications linked to their source data.

Query data and inspect its structured schema without an API key. This example
creates an in-memory inventory database and finds products to restock:

```python
import asyncio

import pandas as pd

from tabulaflow.data import SQLConnector


async def main() -> None:
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    async with stock:
        await stock.write_dataframe_async(
            pd.DataFrame(
                columns=["product", "on_hand", "reorder_point"],
                data=[
                    ("USB-C dock", 3, 10),
                    ("Laptop stand", 18, 8),
                    ("HDMI cable", 4, 12),
                ],
            ),
            "inventory",
        )
        table = stock.schema.tables[0]
        print("Table:", table.name)
        print("Columns:", [(column.name, column.dtype) for column in table.columns])

        result = await stock.run_query_async(
            "SELECT product, reorder_point - on_hand AS units_to_order "
            "FROM inventory WHERE on_hand < reorder_point ORDER BY product"
        )
        if result.error is not None:
            raise RuntimeError(result.error.message)
        print("DataFrame:\n", result.df)


if __name__ == "__main__":
    asyncio.run(main())
```

[Python library guide](https://megagonlabs.github.io/tabulaflow/python-library/quick-start/)

## TabulaFlow for Researchers

TabulaFlow Research extends the main Python library for AI and database researchers working
on text-to-SQL and data agents. Its main building blocks include benchmark
loaders, agents, evaluation metrics, and experiment pipelines. It is
designed around principles that enable flexible, rapid, and transparent
experiments:

- **Benchmark-ready.** Run BIRD-SQL, Spider 2.0, Beaver, ARCS, AMBROSIA-S, and
  CypherBench with managed setup and official leaderboard metrics.
- **Reusable agent logic.** One agent implementation runs on all benchmarks.
- **Transparent and fully typed.** Work with typed tasks, schemas, and
  predictions rather than black-box dictionaries or schema strings. Write
  Python instead of YAML.
- **Async-native for large-scale concurrency.** Task inference, LLM calls, and
  database queries are async and parallelizable, with configurable concurrency
  controls that can make full use of provider limits.
- **Modular and extensible.** Use any building blocks you need, or extend them by
  implementing their public protocols.
- **Built-in tracking.** Record trajectories, token usage, and latency for
  analysis, with optional Langfuse and Phoenix tracing.
- **Simple and performant agents.** Simple yet state-of-the-art agent
  implementations provide a performant starting point.

### Quick start

With the TabulaFlow tool installed and `OPENAI_API_KEY` set, download BIRD-SQL
and run the bundled research example:

```bash
tabulaflow benchmark download bird-sql
tabulaflow examples run research-quick-start
```

To adapt the workflow in your own project, add TabulaFlow with `uv add
tabulaflow`, then run experiments from Python:

```python
import asyncio

from tabulaflow.research.agents import BasicAgentConfig, FullSchemaAgent
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async
from tabulaflow.research.types import SimpleNL2QTaskOutput


async def main() -> None:
    dataset = await BirdSQLDatasetLoader().get_split_async(
        "dev",
        databases=["california_schools"],
        subsample_size=3,
    )

    try:
        result = await predict_async(
            FullSchemaAgent,
            BasicAgentConfig(),
            dataset,
            batch_size=3,
        )
        await execute_async(result, dataset, batch_size=3)
        first = result.tasks[0]
        assert isinstance(first, SimpleNL2QTaskOutput)
        assert first.pred_query is not None
        assert first.pred_query.exec_result is not None
        print("Question:", first.question)
        print("Predicted SQL:", first.pred_query.query)
        print("Query result:")
        print(first.pred_query.exec_result.df)

        await evaluate_async(result, dataset, metrics=[BirdSQLEx()], batch_size=3)
        print("Execution accuracy:", result.aggregated_eval_metrics["bird_sql_ex"]["avg"])
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
```

To keep the predictions, scores, and readable reports together, save the result
after evaluation inside the `try` block:

```python
result.to_directory("runs/full-schema")
```

The saved run has this structure:

```text
runs/full-schema/
├── result.json
├── result_summary.csv
└── readable/
    └── <qid>/
        ├── task_readable.md
        └── trajectory/
            └── <trajectory-id>.md
```

Inspect queries, scores, agent trajectories, token usage, and latency without
rerunning the agent.

[Research toolkit guide](https://megagonlabs.github.io/tabulaflow/research-toolkit/quick-start/)

## Disclosures

This software may include, incorporate, or access open source software (OSS) components,
datasets and other third party components, including those identified below. The license terms
respectively governing the datasets and third-party components continue to govern those
portions, and you agree to those license terms may limit any distribution, use, and copying.
You may use any OSS components under the terms of their respective licenses, which may
include BSD 3, Apache 2.0, and other licenses. In the event of conflicts between Megagon Labs,
Inc. (“Megagon”) license conditions and the OSS license conditions, the applicable OSS
conditions governing the corresponding OSS components shall prevail.
You agree not to, and are not permitted to, distribute actual datasets used with the OSS
components listed below. You agree and are limited to distribute only links to datasets from
known sources by listing them in the datasets overview table below. You agree that any right to
modify datasets originating from parties other than Megagon are governed by the respective
third party’s license conditions.
You agree that Megagon grants no license as to any of its intellectual property and patent rights.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS (INCLUDING
MEGAGON) “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. You agree to cease using,
incorporating, and distributing any part of the provided materials if you do not agree with the
terms or the lack of any warranty herein.
While Megagon makes commercially reasonable efforts to ensure that citations in this
document are complete and accurate, errors may occur. If you see any error or omission, please
help us improve this document by sending information to contact_oss@megagon.ai.

<details>
<summary><strong>Research benchmark datasets</strong></summary>

Benchmark data is downloaded separately unless noted below and remains subject to
the upstream license and access terms.

| Benchmark | Included | Upstream | License / terms |
|---|---|---|---|
| BIRD-SQL | No | [BIRD-SQL](https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/bird) | CC BY-SA 4.0 |
| AMBROSIA | No | [AMBROSIA](https://github.com/saparina/ambrosia) | CC BY 4.0; upstream asks that the dataset not be uploaded to GitHub or Hugging Face. |
| Spider 2.0 (Lite, Snow, DBT) | No | [Spider 2.0](https://github.com/xlang-ai/Spider2) | MIT; hosted database access is subject to provider terms. |
| BEAVER | No | [BEAVER](https://github.com/peterbaile/beaver-may-2025) | MIT; separately hosted database dumps are subject to upstream terms. |
| CypherBench | No | [CypherBench](https://huggingface.co/datasets/megagonlabs/cypherbench) | Apache-2.0; graph data is derived from Wikidata (CC0). |

</details>

<details>
<summary><strong>Open source software components</strong></summary>

TabulaFlow uses the unmodified direct runtime dependencies below. Transitive
Python dependencies and exact resolved versions are recorded in
[`uv.lock`](uv.lock). License notices for JavaScript components bundled with the
application are included alongside those files under
[`tabulaflow/app/pane/assets/vendor`](tabulaflow/app/pane/assets/vendor).

| Component | Modified | Upstream | License |
|---|---:|---|---|
| aiolimiter | No | [mjpieters/aiolimiter](https://github.com/mjpieters/aiolimiter) | MIT |
| aiosqlite | No | [omnilib/aiosqlite](https://github.com/omnilib/aiosqlite) | MIT |
| arize-phoenix-otel | No | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | Apache-2.0 |
| asyncmy | No | [long2ice/asyncmy](https://github.com/long2ice/asyncmy) | Apache-2.0 |
| asyncpg | No | [MagicStack/asyncpg](https://github.com/MagicStack/asyncpg) | Apache-2.0 |
| datasets | No | [huggingface/datasets](https://github.com/huggingface/datasets) | Apache-2.0 |
| dbt-duckdb | No | [duckdb/dbt-duckdb](https://github.com/duckdb/dbt-duckdb) | Apache-2.0 |
| duckdb | No | [duckdb/duckdb-python](https://github.com/duckdb/duckdb-python) | MIT |
| duckdb-engine | No | [Mause/duckdb_engine](https://github.com/Mause/duckdb_engine) | MIT |
| filelock | No | [tox-dev/filelock](https://github.com/tox-dev/filelock) | Unlicense |
| gdown | No | [wkentaro/gdown](https://github.com/wkentaro/gdown) | MIT |
| genai-prices | No | [pydantic/genai-prices](https://github.com/pydantic/genai-prices) | MIT |
| google-cloud-bigquery-storage | No | [googleapis/python-bigquery-storage](https://github.com/googleapis/python-bigquery-storage) | Apache-2.0 |
| httpx | No | [encode/httpx](https://github.com/encode/httpx) | BSD-3-Clause |
| huggingface-hub | No | [huggingface/huggingface_hub](https://github.com/huggingface/huggingface_hub) | Apache-2.0 |
| Jinja2 | No | [pallets/jinja](https://github.com/pallets/jinja) | BSD-3-Clause |
| langfuse | No | [langfuse/langfuse-python](https://github.com/langfuse/langfuse-python) | MIT |
| markdown-it-py | No | [executablebooks/markdown-it-py](https://github.com/executablebooks/markdown-it-py) | MIT |
| neo4j | No | [neo4j/neo4j-python-driver](https://github.com/neo4j/neo4j-python-driver) | Apache-2.0 and Python-2.0 |
| pandas | No | [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | BSD-3-Clause |
| Pillow | No | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) | MIT-CMU |
| playwright | No | [microsoft/playwright-python](https://github.com/microsoft/playwright-python) | Apache-2.0 |
| plotext | No | [piccolomo/plotext](https://github.com/piccolomo/plotext) | MIT |
| pyarrow | No | [apache/arrow](https://github.com/apache/arrow) | Apache-2.0 |
| pydantic | No | [pydantic/pydantic](https://github.com/pydantic/pydantic) | MIT |
| pydantic-ai-slim | No | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | MIT |
| pydantic-settings | No | [pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) | MIT |
| Pygments | No | [pygments/pygments](https://github.com/pygments/pygments) | BSD-2-Clause |
| PyMySQL | No | [PyMySQL/PyMySQL](https://github.com/PyMySQL/PyMySQL) | MIT |
| pypdf | No | [py-pdf/pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause |
| PyYAML | No | [yaml/pyyaml](https://github.com/yaml/pyyaml) | MIT |
| rich | No | [Textualize/rich](https://github.com/Textualize/rich) | MIT |
| snowflake-connector-python | No | [snowflakedb/snowflake-connector-python](https://github.com/snowflakedb/snowflake-connector-python) | Apache-2.0 |
| snowflake-sqlalchemy | No | [snowflakedb/snowflake-sqlalchemy](https://github.com/snowflakedb/snowflake-sqlalchemy) | Apache-2.0 |
| SQLAlchemy | No | [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) | MIT |
| sqlalchemy-bigquery | No | [googleapis/python-bigquery-sqlalchemy](https://github.com/googleapis/python-bigquery-sqlalchemy) | Apache-2.0 |
| SQLGlot | No | [tobymao/sqlglot](https://github.com/tobymao/sqlglot) | MIT |
| sqlparse | No | [andialbrecht/sqlparse](https://github.com/andialbrecht/sqlparse) | BSD-3-Clause |
| tabulate | No | [astanin/python-tabulate](https://github.com/astanin/python-tabulate) | MIT |
| textual | No | [Textualize/textual](https://github.com/Textualize/textual) | MIT |
| tiktoken | No | [openai/tiktoken](https://github.com/openai/tiktoken) | MIT |
| tqdm | No | [tqdm/tqdm](https://github.com/tqdm/tqdm) | MPL-2.0 and MIT |
| typer | No | [fastapi/typer](https://github.com/fastapi/typer) | MIT |
| webbrowser-open | No | [minrk/webbrowser_open](https://github.com/minrk/webbrowser_open) | BSD-3-Clause |

The application also bundles the following unmodified browser-side components:

| Component | Modified | Upstream | License |
|---|---:|---|---|
| Cytoscape.js | No | [cytoscape/cytoscape.js](https://github.com/cytoscape/cytoscape.js) | MIT |
| cytoscape-dagre | No | [cytoscape/cytoscape.js-dagre](https://github.com/cytoscape/cytoscape.js-dagre) | MIT |
| Dagre | No | [dagrejs/dagre](https://github.com/dagrejs/dagre) | MIT |
| KaTeX | No | [KaTeX/KaTeX](https://github.com/KaTeX/KaTeX) | MIT |
| MapLibre GL JS | No | [maplibre/maplibre-gl-js](https://github.com/maplibre/maplibre-gl-js) | BSD-3-Clause |
| markdown-it | No | [markdown-it/markdown-it](https://github.com/markdown-it/markdown-it) | MIT |
| markdown-it-texmath | No | [goessner/markdown-it-texmath](https://github.com/goessner/markdown-it-texmath) | MIT |
| Tabulator | No | [olifolkerd/tabulator](https://github.com/olifolkerd/tabulator) | MIT |
| Vega | No | [vega/vega](https://github.com/vega/vega) | BSD-3-Clause |
| Vega-Embed | No | [vega/vega-embed](https://github.com/vega/vega-embed) | BSD-3-Clause |
| Vega-Lite | No | [vega/vega-lite](https://github.com/vega/vega-lite) | BSD-3-Clause |

</details>
