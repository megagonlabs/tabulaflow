# Custom agents

Build an agent around your workflow. Combine TabulaFlow's reusable tools with
your own queries and actions, without adopting `ChatSession`.

## Build a customer support agent

A customer support agent needs to explore a directory of FAQs and product
guides, including PDFs with screenshots, and run database queries scoped to
the signed-in customer. TabulaFlow's tools let you provide these capabilities
without exposing a shell tool.

This example helps a customer find their most recent USB-C dock purchase and
troubleshoot a charging issue. The agent finds their purchases, consults the
support documents, and opens a ticket when requested. Build it by combining a
reusable document tool with custom database tools and an action:

- Reuse `ViewTool` to browse the support directory and read text, images, and PDFs.
- Build `find_orders` and `lookup_order` on top of `RunQueryTool.execute(...)`.
  These custom tools search purchases and retrieve delivery status using
  application-owned SQL scoped to the customer.
- Add `open_support_ticket`, which reuses the scoped order lookup to check
  ownership before recording the issue and returning a ticket ID.

The FAQ guides troubleshooting and explains what to include in a ticket.
The ticket tool checks that the order belongs to the signed-in customer.

```python title="custom_agents.py"
--8<-- "examples/custom_agents.py"
```

The search finds two dock purchases. The most recent is order **1001**. The
customer has already tried the guide's steps and requests further help, so
the agent opens ticket **SUP-1**. `SupportReply` separates the customer-facing
message, suggested next steps, document references, and ticket ID. The script
also prints the stored ticket so you can inspect the action.
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

`ViewTool(working_dir=support_dir)` restricts browsing and reading to the
support directory by default. It provides directory listings and reads text,
images, and PDFs without shell access. PDFs and images reach the model as
native content, so it can inspect the guide's settings screenshot alongside
the written steps. The tool can also select PDF pages or text line ranges.

The agent calls `find_orders` and `lookup_order`; `RunQueryTool` executes their
fixed SQL and bound values internally. The agent supplies a product name or
order ID, while the application supplies the authenticated customer identity
and includes it in each query's filter. Search returns purchase dates, newest
first; lookup adds the order's delivery status. If the matches are ambiguous,
the agent can ask the customer instead of guessing.

Both tools return readable results for the model and `QueryExecution` metadata
for your application, including SQL, bound values, and the result DataFrame
or error. They reuse formatting and metrics without exposing unrestricted
queries.

The ticket tool checks ownership each time it is called, even if the agent
skips the earlier lookup, then records the ticket in memory and returns its ID.

In your application, take the customer identity from authentication and replace
the in-memory ticket store with your helpdesk API or persistent storage. Use
[read-only credentials and execution limits](data-connectors.md#control-query-execution)
for order lookups.

## Compose your own workflow

`make_agent(...)` constructs a Pydantic AI agent with TabulaFlow's shared model
throttling. Here, its tool list combines `view.as_pydantic_ai_tool()` with the
custom `find_orders`, `lookup_order`, and `open_support_ticket` functions.
`RunQueryTool` supplies reusable query execution, formatting, and metrics
inside those functions. A Pydantic output model defines the final
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
