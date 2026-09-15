# Build custom agents

Combine TabulaFlow's reusable tools with your own functions and actions in a
Pydantic AI agent.

## Example: Build a customer support agent

Find a customer's order, consult product guides, and open a support ticket.
The script supplies an `orders` database connector, a `support_dir` containing
the FAQ and illustrated PDF guide, and the signed-in `customer_id`.

Reuse document access and query execution, then define a customer-scoped search:

```python
--8<-- "examples/custom_agents.py:tool-imports"

--8<-- "examples/custom_agents.py:tools"

--8<-- "examples/custom_agents.py:find-orders"
```

The same query tool supports order lookup and ownership checks:

??? info "Order lookup"

    ```python
    --8<-- "examples/custom_agents.py:query-order"

    --8<-- "examples/custom_agents.py:lookup-order"
    ```

Add an action that checks ownership and records a ticket:

```python
--8<-- "examples/custom_agents.py:ticket"
```

Combine the tools and declare the response your application receives:

```python
--8<-- "examples/custom_agents.py:agent-imports"

--8<-- "examples/custom_agents.py:reply"

--8<-- "examples/custom_agents.py:agent"
```

Run the agent and inspect its structured response:

```python
--8<-- "examples/custom_agents.py:request"
```

Expect order **1001** and ticket **SUP-1**. Wording and tool-call order may vary.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run the complete example:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/custom_agents.py
```

The script creates the database and temporary document directory, loads the
bundled FAQ and PDF guide, and closes its resources. Use a model with PDF input
support; tickets are stored in memory for this example.
