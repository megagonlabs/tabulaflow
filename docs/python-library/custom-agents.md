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

Expect the agent to find order **1001** and create ticket **SUP-1**. The script
prints the reply, suggested steps, document references, and stored ticket.
Wording and tool-call order may vary.

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/custom_agents.py
```

The script creates an in-memory SQLite database and temporary support directory,
using the bundled [FAQ](../examples/support/faq.txt) and
[PDF guide](../examples/support/dock-guide.pdf) from a checkout, or downloading
them when run from the URL above. Use a model with PDF input support. Tickets
are stored in memory for the duration of the run.
