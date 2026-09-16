# Chat sessions

Use `ChatSession` for conversations across data sources, with retained context,
structured outputs, and streaming answers and tool progress.

## Example: Ask a follow-up question

You're reviewing inventory before placing an order. Ask which products need
restocking, then follow up with how many units to order using the same conversation.

??? example-details "Create the sample database"

    ```python
    --8<-- "examples/chat_sessions.py:data-imports"

    --8<-- "examples/chat_sessions.py:connect"
    --8<-- "examples/chat_sessions.py:registry"
    --8<-- "examples/chat_sessions.py:sample-data"
    ```

```python
--8<-- "examples/chat_sessions.py:session-imports"

--8<-- "examples/chat_sessions.py:session"

--8<-- "examples/chat_sessions.py:first-turn"
```

Reuse the session for the follow-up below; it retains the first question and answer.

## Stream answers and progress

Ask how much to order, using the previous turn's context:

```python
--8<-- "examples/chat_sessions.py:stream"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-chat-sessions.txt"
    ```

`turn_finished` provides the complete result, including its output artifacts and usage. See the
[event reference](api/agents.md#events-and-turn-results) for all event types.

Inspect the completed turn's token usage and estimated API cost:

```python
--8<-- "examples/chat_sessions.py:usage"
```

Set [`OPENAI_API_KEY`](quick-start.md#try-it-yourself), then run both turns:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/chat_sessions.py
```

## Manage a conversation

Start a new conversation while keeping the session's connectors and stored outputs:

```python
--8<-- "examples/chat_sessions.py:reset"
```

Long conversations use automatic context compaction. `ChatSession` and
`DataConnectorRegistry` are async context managers; closing the registry closes
the connectors registered with it. See the
[session reference](api/agents.md#chat-sessions) for configuration and lifecycle
details.
