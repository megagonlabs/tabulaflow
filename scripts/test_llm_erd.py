import time
import asyncio
import json
import os
from mintq.db_connector.snowflake_conn import SnowflakeConnector
from mintq.visualization import er_diagram_to_graphviz
from mintq.metadata_synthesizer import LLMERDiagramSynthesizer


async def main() -> None:
    t0 = time.time()
    connector = SnowflakeConnector.from_credentials_async(
        "AIRLINES",
        os.environ["SF_USER"],
        os.environ["SF_PASSWORD"],
        os.environ["SF_ACCOUNT"],
        "AIRLINES",
    )
    synthesizer = LLMERDiagramSynthesizer()
    erd = synthesizer.run(connector)
    print(json.dumps(erd.model_dump(), indent=2))
    print(f"Time taken: {time.time() - t0} seconds")

    g = er_diagram_to_graphviz(erd)
    g.render("erd", format="png")


if __name__ == "__main__":
    asyncio.run(main())
