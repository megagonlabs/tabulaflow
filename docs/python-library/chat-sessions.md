# Chat sessions

`ChatSession` gives your application a stateful data conversation, including
tools, structured outputs, and streaming events. Reuse the same session for
follow-up questions; it keeps the conversation history for you.

## Example: Ask a follow-up question

First identify products that need restocking, then stream a follow-up about
order quantities. The second question refers to the first answer without
repeating the inventory details.

```python title="chat_sessions.py"
--8<-- "examples/chat_sessions.py"
```

Expect **8 HDMI cables** and **7 USB-C docks** in the follow-up answer. Wording
and tool calls may vary.

Set `OPENAI_API_KEY` as shown in the [quick start](quick-start.md#try-it-yourself),
then run:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/chat_sessions.py
```

This makes paid model calls and sends questions, schema, and relevant query
results to the provider.

## Consume the stream

The example handles three event kinds:

- `tool_started` identifies a tool call, so you can show progress.
- `answer_delta` carries a chunk of the answer.
- `turn_finished` carries the complete `ChatResult`, including text, output
  artifacts, and usage. It ends a successfully completed turn.

Other [events](api/agents.md#events-and-turn-results) report tool progress,
narration, and context compaction. Use `run(...)` when you only need the final
result, or see [Structured outputs](structured-outputs.md) to work with artifacts.

## Manage a conversation

- Create one session per conversation and run one turn at a time. Add sources
  to its registry for [multi-source conversations](quick-start.md#example-chat-with-two-data-sources).
- Set `model`, `reasoning`, and `extra_instructions` when constructing the
  session. Automatic context compaction is enabled by default for long
  conversations; pass `compaction=None` to disable it.
- Use `reset_conversation()` to clear the conversation while keeping the
  session environment, including its connectors and stored outputs.
- Failures propagate as exceptions. To interrupt a turn, cancel and await the
  task consuming the stream before starting another turn.

Close the session with `aclose()` and close your connectors separately. The
nested `finally` blocks above release both even if a turn fails.

See the [ChatSession reference](api/agents.md#chat-sessions) for configuration,
or [Tools and custom agents](tools-and-custom-agents.md) to assemble your own workflow.
