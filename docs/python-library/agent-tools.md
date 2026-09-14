# Agent tools

Give your agent tools for querying data, creating visualizations, and extracting
information from documents. Reuse them alongside your own Python functions,
without adopting `ChatSession`.

## Example: Structured restock plan

Combine `RunQueryTool` with your own ordering logic to produce a typed restock
plan. A Python function rounds orders to whole supplier packs, and a Pydantic
model defines the final response.

```python title="custom_agents.py"
--8<-- "examples/custom_agents.py"
```

The dock shortfall is 7, rounded to **8 units** in packs of 4. The cable
shortfall is 8, rounded to **10 units** in packs of 5. Expect those two products
and **18 total units**; product order and query count may vary.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/custom_agents.py
```

The example closes its connector in `finally`. For your own data, use
[read-only credentials and execution limits](data-connectors.md#control-query-execution).

## Reuse tools in your agent

`make_agent(...)` constructs a Pydantic AI agent with TabulaFlow's shared model
throttling. `as_pydantic_ai_tool()` adapts a TabulaFlow tool for that agent;
ordinary tool functions such as `order_in_packs` can sit alongside it.

For direct Python use, `await query_tool.execute(query)` returns a
`QueryExecution` with formatted text and an `ExecResult`. Check
`execution.exec_result.error` before consuming the data. Other tools have
their own return types and error behavior.

Use [registry-aware tools](api/agents.md#data-tools) when the agent should choose
among multiple connectors. Add [visualization tools](api/agents.md#output-tools)
for artifacts, or [extraction and enrichment tools](api/agents.md#extraction-and-enrichment-tools)
for document workflows.

## Add your own tools

A plain function is enough for a Pydantic AI tool, as above. For a reusable
TabulaFlow tool, follow the [AgentTool contract](api/agents.md#tool-contracts):
expose `name`, `__call__`, `as_pydantic_ai_tool()`, and `metrics()`. Keep reusable
work in `execute(...)` and use `__call__` to adapt its result or expected errors
for the model.

The example's `RestockPlan` is a typed answer, not an artifact specification.
Use [structured outputs](structured-outputs.md) for tables and charts with
resolvable data, or [Chat sessions](chat-sessions.md) for a conversation runtime
that integrates tools and artifacts.
