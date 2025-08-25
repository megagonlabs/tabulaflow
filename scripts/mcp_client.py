"""MCP Streamable HTTP Client"""

import argparse
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class MCPClient:
    """MCP Client for interacting with an MCP Streamable HTTP server"""

    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_streamable_http_server(self, server_url: str, headers: Optional[dict] = None):
        """Connect to an MCP server running with HTTP Streamable transport"""
        self._streams_context = streamablehttp_client(  # pylint: disable=W0201
            url=server_url,
            headers=headers or {},
        )
        read_stream, write_stream, _ = await self._streams_context.__aenter__()  # pylint: disable=E1101

        self._session_context = ClientSession(read_stream, write_stream)  # pylint: disable=W0201
        self.session: ClientSession = await self._session_context.__aenter__()  # pylint: disable=C2801

        await self.session.initialize()

    async def list_tools(self):
        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]
        return available_tools

    async def test_run_query(self, query: str):
        response = await self.session.call_tool("run_query", {"query": query})
        return response.content

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:  # pylint: disable=W0125
            await self._streams_context.__aexit__(None, None, None)  # pylint: disable=E1101


async def main():
    """Main function to run the MCP client"""
    parser = argparse.ArgumentParser(description="Run MCP Streamable http based Client")
    parser.add_argument("--mcp-localhost-port", type=int, default=8125, help="Localhost port to bind to")
    args = parser.parse_args()

    client = MCPClient()

    try:
        await client.connect_to_streamable_http_server(f"http://10.0.175.210:{args.mcp_localhost_port}/mcp/")
        print(await client.list_tools())
        print(await client.test_run_query("SELECT * FROM job_seeker LIMIT 10"))
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
