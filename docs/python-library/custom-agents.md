# Build custom agents

Combine TabulaFlow's reusable tools with your own functions and actions in a
Pydantic AI agent.

## Example: Build a customer support agent

A customer's USB-C dock won't charge their laptop, and they cannot find the
order number. Build an agent that finds the order, consults product guides,
and opens a support ticket.

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
