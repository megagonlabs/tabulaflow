from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mini", host="0.0.0.0", port=8124, json_response=False, stateless_http=False)


async def get_schema() -> str:
    return "Courses(id: int, name: str, description: str)"


PSEUDO_RESULT = """
id  name  description
----
1   Math  Math course
2   Science Science course
"""


async def execute_query(query: str) -> str:
    return PSEUDO_RESULT


mcp.add_tool(get_schema, name="get_schema")
mcp.add_tool(execute_query, name="execute_query")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
