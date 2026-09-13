# Tools and custom agents

Bring TabulaFlow tools into your own agent when you want control over the
instructions, available actions, and response type. You do not need
`ChatSession` to use them.

## Plan an order in supplier packs

Give a custom agent a query tool and a small Python function for rounding
orders to whole packs. A Pydantic model makes its final restocking plan
available as typed Python data.

```python title="custom_agents.py"
--8<-- "examples/custom_agents.py"
```

The dock shortfall is 7, rounded to **8 units** in packs of 4. The cable
shortfall is 8, rounded to **10 units** in packs of 5. Expect those two products
and **18 total units**; product order and query count may vary.

Set `OPENAI_API_KEY` as shown in the [quick start](quick-start.md#try-it-yourself),
then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/custom_agents.py
```

This makes paid model calls and sends the schema, question, and query results
to the provider. The database is disposable; use appropriately restricted
credentials when connecting an agent to your own data.

## Choose what to reuse

`make_agent(...)` constructs a Pydantic AI agent with TabulaFlow's shared model
throttling. `as_pydantic_ai_tool()` adapts a TabulaFlow tool for that agent;
ordinary tool functions such as `order_in_packs` can sit alongside it.

For direct Python use, `await query_tool.execute(query)` returns a
`QueryExecution` with formatted text and an `ExecResult`. Check
`execution.exec_result.error` before consuming the data. Other tools have
their own return types and error behavior.

Use [registry-aware tools](api/agents.md#data-tools) when the agent should choose
among multiple connectors. Add [extraction and enrichment tools](api/agents.md#extraction-and-enrichment-tools)
or call [extraction services](api/agents.md#extraction-and-summarization) directly
for document workflows.

## Add your own tools

A plain function is enough for a Pydantic AI tool, as above. For a reusable
TabulaFlow tool, follow the [AgentTool contract](api/agents.md#tool-contracts):
keep reusable work in `execute(...)`, expose the model-facing adapter through
`__call__`, and provide `as_pydantic_ai_tool()` and metrics.

This custom agent returns a `RestockPlan`, not a `ChatResult`. Add
[structured outputs](structured-outputs.md) explicitly when your application
needs artifacts, or use [ChatSession](chat-sessions.md) for the integrated
conversation runtime.
