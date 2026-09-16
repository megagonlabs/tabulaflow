# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulaflow==0.1.0", "pandas>=2.2.3"]
# ///

import asyncio

# --8<-- [start:data-imports]
import pandas as pd

from tabulaflow.data import SQLConnector

# --8<-- [end:data-imports]
# --8<-- [start:store-imports]
from tabulaflow.data import DataConnectorRegistry
from tabulaflow.output.store import OutputStore

# --8<-- [end:store-imports]
# --8<-- [start:resolve-imports]
from tabulaflow.output.resolver import OutputResolver, ResolvedGraphArtifact, ResolvedTableArtifact, UnavailableArtifact

# --8<-- [end:resolve-imports]
# --8<-- [start:parameter-imports]
from tabulaflow.output.specs import NumberParameter

# --8<-- [end:parameter-imports]
# --8<-- [start:artifact-imports]
from tabulaflow.output.specs import GraphArtifactSpec, OutputSpec, TableArtifactSpec
# --8<-- [end:artifact-imports]


async def load_sample_data(logistics):
    # --8<-- [start:sample-data]
    await logistics.write_dataframe_async(
        pd.DataFrame(
            columns=["origin", "destination", "units"],
            data=[
                ("Chicago", "Dallas", 500),
                ("Chicago", "Denver", 200),
                ("Dallas", "Austin", 350),
                ("Denver", "Seattle", 80),
            ],
        ),
        "transfers",
    )
    # --8<-- [end:sample-data]


async def main():
    # --8<-- [start:connect]
    logistics = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    # --8<-- [end:connect]
    try:
        await load_sample_data(logistics)
        # --8<-- [start:store]
        registry = DataConnectorRegistry()
        registry.register("logistics", logistics)
        store = OutputStore(registry=registry)
        # --8<-- [end:store]

        # --8<-- [start:source]
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
        # --8<-- [end:source]
        # --8<-- [start:artifacts]
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
        # --8<-- [end:artifacts]

        # --8<-- [start:resolve]
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
        # --8<-- [end:resolve]

        print("Output JSON:", output.model_dump_json())
    finally:
        await logistics.close_async()


if __name__ == "__main__":
    asyncio.run(main())
