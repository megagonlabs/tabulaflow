# Build custom agents

Combine TabulaFlow's reusable tools with your own functions and actions in a
Pydantic AI agent.

## Example: Build a customer support agent

A customer's USB-C dock won't charge their laptop, and they cannot find the
order number. Build an agent that finds the order, consults product guides,
and opens a support ticket.

```python title="custom_agents.py"
--8<-- "tabulaflow/examples/custom_agents.py:example"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-custom-agent.txt"
    ```

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run the complete example:

```bash
tabulaflow examples run custom-agents
```

The example intentionally keeps application concerns lightweight: the signed-in
customer is fixed, and tickets are stored in memory. In a real application,
derive customer identity from authentication and persist tickets in your support
system. Use a model with PDF input support.
