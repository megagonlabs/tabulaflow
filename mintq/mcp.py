import argparse
import asyncio
from mintq.datahub import get_dataset_loader
from mintq.toolhub import RunQueryTool
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("mintq", host="0.0.0.0", port=8125)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="spider2-snow")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--database", default="AIRLINES")
    args = parser.parse_args()

    dataset_loader = get_dataset_loader(args.dataset)
    dataset = await dataset_loader.get_split_async(args.split, databases=[args.database])
    db_connector = dataset.db_connectors[args.database]
    run_query_tool = RunQueryTool(db_connector=db_connector)

    mcp.add_tool(run_query_tool.__call__, name="run_query")


if __name__ == "__main__":
    asyncio.run(main())
    mcp.run(transport="streamable-http")
