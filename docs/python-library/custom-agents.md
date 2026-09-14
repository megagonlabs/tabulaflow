# Custom agents

Build an agent around your workflow. Combine TabulaFlow's reusable tools with
your own queries and actions, without adopting `ChatSession`.

## Example: Customer support agent

Help a customer who cannot find the order number for their newer dock. The
agent finds matching purchases, checks the selected order, reads a text FAQ
and an illustrated PDF, and opens a ticket when eligible.

- `ViewTool` browses the support directory and reads text, images, and PDFs.
- `find_orders` searches product names and returns purchase dates, newest first.
- `lookup_order` retrieves the selected order's product and delivery status.
- `open_support_ticket` checks ownership and delivery status, then records the issue.

The example's policy allows a technical-support ticket only when the customer
owns a delivered order, requests support, and confirms that the guide's steps
have not solved the problem. Otherwise, the agent suggests those steps or asks
what they tried. Asking for a ticket alone is not enough.

```python title="custom_agents.py"
--8<-- "examples/custom_agents.py"
```

The search finds two dock purchases. The newer one is order **1001**, and its
lookup confirms delivery. The customer has already tried the guide's steps,
so the request qualifies for ticket **SUP-1001**. `SupportReply` separates the
customer-facing message, suggested next steps, document references, and ticket
ID. The script also prints the stored ticket so you can inspect the action.
Wording, references, and tool-call order may vary; suggested steps can be empty
when no further troubleshooting is documented.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/custom_agents.py
```

The script prepares an in-memory SQLite database and a temporary support
directory. It uses the bundled [FAQ](../examples/support/faq.txt) and
[PDF guide](../examples/support/dock-guide.pdf) from a checkout, or downloads
them when run directly. Use a model with PDF input support. No external
helpdesk is contacted; demo tickets exist only for the duration of the run.

## Choose what your agent can do

`ViewTool` is restricted to the support directory by default. PDFs and images
reach the model as native content rather than flattened text; the tool can
also select PDF pages or text line ranges.

Search and lookup both reuse `RunQueryTool.execute(...)` with fixed SQL and
bound values. The agent supplies a product name or order ID, never SQL or a
customer identity. Search returns summaries; lookup adds the delivery status
needed for the ticket policy. If the matches are ambiguous, the agent can ask
the customer instead of guessing.

Both tools return readable results for the model and `QueryExecution` metadata
for your application, including SQL, bound values, and the result DataFrame
or error. They reuse formatting and metrics without exposing unrestricted
queries.

The prompt and FAQ guide escalation based on the customer's account of what
they tried. The tool independently enforces ownership and delivery status,
and reuses an existing ticket for the same order. These checks do not depend
on the agent following its instructions.

In your application, take the customer identity from authentication and replace
the in-memory ticket store with your helpdesk API or persistent storage. Use
[read-only credentials and execution limits](data-connectors.md#control-query-execution)
for order lookups.

## Compose your own workflow

`make_agent(...)` constructs a Pydantic AI agent with TabulaFlow's shared model
throttling. `as_pydantic_ai_tool()` adapts a built-in tool; your own typed Python
functions can sit alongside it. A Pydantic output model defines the final
response your application receives. Schema validation checks its shape, not
whether its citations or claimed actions are correct; verify those against
the documents and tool results before relying on them.

Add [query tools](api/agents.md#data-tools) for open-ended analysis,
[visualization tools](api/agents.md#output-tools) for artifacts, or
[extraction tools](api/agents.md#extraction-and-enrichment-tools) for document
workflows. For a reusable tool class, follow the
[AgentTool contract](api/agents.md#tool-contracts).

`SupportReply` is a typed answer, not an artifact specification. Use
[structured outputs](structured-outputs.md) for tables and charts with resolvable
data, or [Chat sessions](chat-sessions.md) for an integrated conversation runtime.
