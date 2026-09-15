# Build custom agents

Combine TabulaFlow's reusable tools with your own functions and actions in a
Pydantic AI agent.

## Example: Build a customer support agent

Find a customer's order, consult product guides, and open a support ticket.
Reuse `ViewTool` for documents and `RunQueryTool` for customer-scoped queries,
then add a ticket action and a typed response:

```python title="custom_agents.py"
--8<-- "examples/custom_agents.py:example"
```

Expect order **1001** and ticket **SUP-1**. Wording and tool-call order may vary.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run the complete example:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/custom_agents.py
```

The script creates the database and temporary document directory, loads the
bundled FAQ and PDF guide, and closes its resources. Use a model with PDF input
support; tickets are stored in memory for this example.
