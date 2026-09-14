# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

import pandas as pd

from tabulaflow.data import DataConnectorRegistry, SQLConnector
from tabulaflow.output.resolver import OutputResolver, ResolvedGraphArtifact, ResolvedTableArtifact, UnavailableArtifact
from tabulaflow.output.specs import GraphArtifactSpec, NumberParameter, OutputSpec, TableArtifactSpec
from tabulaflow.output.store import OutputStore


async def load_sample_data(logistics):
    await logistics.write_dataframe_async(
        pd.DataFrame(
            {
                "origin": ["Chicago", "Chicago", "Dallas", "Denver"],
                "destination": ["Dallas", "Denver", "Austin", "Seattle"],
                "units": [500, 200, 350, 80],
            }
        ),
        "transfers",
    )


async def main():
    logistics = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    try:
        await load_sample_data(logistics)
        registry = DataConnectorRegistry()
        registry.register("logistics", logistics)
        store = OutputStore(registry=registry)

        min_units = NumberParameter(
            id="min_units",
            label="Minimum units transferred",
            min=0,
            max=500,
            step=50,
            default=100,
        )
        source = store.add_parameterized_artifact_source(
            connector_alias="logistics",
            parameters=[min_units],
            query_template=(
                "SELECT origin, destination, units FROM transfers "
                "WHERE units >= {{ min_units }} ORDER BY origin, destination"
            ),
        )
        graph = GraphArtifactSpec(
            id="transfer_graph",
            source_ids=[source.id],
            spec={
                "nodes": [
                    {"source_id": source.id, "id": "origin"},
                    {"source_id": source.id, "id": "destination"},
                ],
                "edges": [{"source_id": source.id, "source": "origin", "target": "destination", "label": "units"}],
            },
        )
        output = OutputSpec(
            parameters=[min_units],
            sources=[source],
            artifacts=[TableArtifactSpec(id="transfer_table", source_id=source.id), graph],
        )

        resolver = OutputResolver(store)
        for threshold in (100, 300, 100):
            resolved = await resolver.resolve(output, {"min_units": threshold})
            print("Selection:", resolved.selection)
            for artifact in resolved.artifacts:
                if isinstance(artifact, UnavailableArtifact):
                    print("Unavailable:", artifact.artifact_id, artifact.reason)
                elif isinstance(artifact, ResolvedTableArtifact):
                    print("Result ID:", artifact.result.metadata.id)
                    print("SQL:", artifact.result.metadata.query)
                    print("DataFrame:\n", artifact.result.df)
                elif isinstance(artifact, ResolvedGraphArtifact):
                    print("Graph nodes:", [node.id for node in artifact.graph.nodes])
                    print("Graph edges:", [(edge.source, edge.target, edge.label) for edge in artifact.graph.edges])

        print("Output JSON:", output.model_dump_json())
    finally:
        await logistics.close_async()


if __name__ == "__main__":
    asyncio.run(main())
