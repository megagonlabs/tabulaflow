# TabulaFlow

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize, or transform across databases, spreadsheets and other
local files, public datasets, and the web. Like a general-purpose coding agent,
it can also write code, work with files, run shell commands, and browse the web.

[Documentation](https://megagonlabs.github.io/tabulaflow/) |
[Python library](#python-library) | [Research toolkit](#research-toolkit)

Requires Python 3.11 or later on macOS or Linux. Install with
[`uv`](https://docs.astral.sh/uv/), set your API key, and launch from your
working directory:

```bash
uv tool install tabulaflow
export OPENAI_API_KEY="your-api-key"
tabulaflow
```

The app includes sample data. Try:

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

The result opens as an interactive chart, with its underlying data and query
available for inspection. Use `/connect` to add your own data.

For web browsing, also install Chromium:

```bash
uv tool run --from playwright playwright install chromium
```

[Data agent guide](https://megagonlabs.github.io/tabulaflow/#get-started)

TabulaFlow 0.1.0 is a public beta. Minor `0.x` releases may contain documented
breaking changes.

## Python library

Build data agents with reusable connectors, tools, and structured outputs.
Use the components independently or combine them in a `ChatSession` to work
across multiple data sources. Connectors and outputs also work without an LLM.

Add TabulaFlow to your Python project:

```bash
uv add tabulaflow
```

With `OPENAI_API_KEY` set, create an in-memory database, ask for a chart, and
inspect the SQL and DataFrame behind it:

```python
import asyncio

import pandas as pd

from tabulaflow.agents import ChatSession
from tabulaflow.data import DataConnectorRegistry, SQLConnector


async def main():
    sales = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    await sales.write_dataframe_async(
        pd.DataFrame(
            columns=["region", "revenue_usd"],
            data=[
                ("West", 1200),
                ("West", 800),
                ("East", 1500),
            ],
        ),
        "sales",
    )
    registry = DataConnectorRegistry()
    registry.register("sales", sales)
    session = ChatSession(registry=registry, model="openai-responses:gpt-5-mini", reasoning="low")

    result = await session.run("Show total revenue by region as a bar chart.")
    print("Answer:", result.text)
    for artifact in result.output.artifacts:
        if artifact.kind == "chart":
            data = await session.output_store.resolve_artifact_source(artifact.source_id)
            print("SQL:", data.metadata.query)
            print("DataFrame:\n", data.df)

    await session.aclose()
    await sales.close_async()


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


async def main():
    stock = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    try:
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
        for table in stock.schema.tables:
            print("Table:", table.name)
            for column in table.columns:
                print(f"  {column.name}: {column.dtype}, examples={column.examples}")

        result = await stock.run_query_async(
            "SELECT product, reorder_point - on_hand AS units_to_order "
            "FROM inventory WHERE on_hand < reorder_point ORDER BY product"
        )
        if result.error is not None:
            raise RuntimeError(result.error.message)
        print(result.df)
    finally:
        await stock.close_async()


asyncio.run(main())
```

[Python library guide](https://megagonlabs.github.io/tabulaflow/python-library/quick-start/)

## Research toolkit

TabulaFlow Research extends the main Python library for AI researchers working
on text-to-SQL and data agents. Its benchmark loaders, agents, evaluation
metrics, and experiment pipelines support flexible, rapid, and transparent
experiments.

Reuse agent logic across BIRD-SQL, Spider 2.0, Beaver, ARCS, AMBROSIA, and
CypherBench, with managed benchmark setup and metrics adapted from official
evaluation implementations.

With the TabulaFlow tool installed and `OPENAI_API_KEY` set, download BIRD-SQL
and run the bundled research example:

```bash
tabulaflow benchmark download bird-sql
tabulaflow examples run research-quick-start
```

To adapt the workflow in your own project, add TabulaFlow with `uv add
tabulaflow`, then run and save experiments from Python:

```python
import asyncio

from tabulaflow.research.agents import BasicAgentConfig, FullSchemaAgent
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async


async def main():
    dataset = await BirdSQLDatasetLoader().get_split_async(
        "dev",
        databases=["california_schools"],
        subsample_size=3,
    )
    try:
        result = await predict_async(FullSchemaAgent, BasicAgentConfig(), dataset, batch_size=3)
        await execute_async(result, dataset, batch_size=3)
        await evaluate_async(result, dataset, metrics=[BirdSQLEx()], batch_size=3)
        print("Execution accuracy:", result.aggregated_eval_metrics["bird_sql_ex"]["avg"])
        result.to_directory("runs/full-schema")
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


asyncio.run(main())
```

Work with typed tasks, schemas, and predictions. Saved runs keep results and
readable reports together:

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

## Open Source Software (OSS) Components

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
