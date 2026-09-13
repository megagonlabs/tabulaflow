# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio
import json

import pandas as pd

from tabulaflow.data import DataConnectorRegistry, SQLConnector
from tabulaflow.output.resolver import OutputResolver, ResolvedTableArtifact, UnavailableArtifact
from tabulaflow.output.specs import ChartArtifactSpec, ChoiceOption, ChoiceParameter, OutputSpec, TableArtifactSpec
from tabulaflow.output.store import OutputStore


async def load_sample_data(sales):
    await sales.write_dataframe_async(
        pd.DataFrame(
            {
                "region": ["West", "West", "East"],
                "revenue_usd": [1200, 800, 1500],
                "profit_usd": [240, 160, 450],
            }
        ),
        "sales",
    )


async def main():
    sales = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    try:
        await load_sample_data(sales)
        registry = DataConnectorRegistry()
        registry.register("sales", sales)
        store = OutputStore(registry=registry)

        metric = ChoiceParameter(
            id="metric",
            label="Metric",
            choices=[
                ChoiceOption(id="revenue_usd", label="Revenue"),
                ChoiceOption(id="profit_usd", label="Profit"),
            ],
        )
        source = store.add_parameterized_artifact_source(
            connector_alias="sales",
            parameters=[metric],
            query_template="SELECT region, SUM({{ metric }}) AS amount FROM sales GROUP BY region ORDER BY region",
        )
        chart = ChartArtifactSpec(
            id="regional_chart",
            source_id=source.id,
            spec={
                "mark": "bar",
                "encoding": {
                    "x": {"field": "region", "type": "nominal"},
                    "y": {"field": "amount", "type": "quantitative"},
                },
            },
        )
        output = OutputSpec(
            parameters=[metric],
            sources=[source],
            artifacts=[TableArtifactSpec(id="regional_table", source_id=source.id), chart],
        )

        resolver = OutputResolver(store)
        for metric_id in ("revenue_usd", "profit_usd", "revenue_usd"):
            resolved = await resolver.resolve(output, {"metric": metric_id})
            print("Selection:", resolved.selection)
            for artifact in resolved.artifacts:
                if isinstance(artifact, UnavailableArtifact):
                    print("Unavailable:", artifact.artifact_id, artifact.reason)
                elif isinstance(artifact, ResolvedTableArtifact):
                    print("Result ID:", artifact.result.metadata.id)
                    print("SQL:", artifact.result.metadata.query)
                    print("DataFrame:\n", artifact.result.df)

        print("Vega-Lite:", json.dumps(chart.spec, indent=2))
        print("Output JSON:", output.model_dump_json())
    finally:
        await sales.close_async()


if __name__ == "__main__":
    asyncio.run(main())
