"""Agent trajectories, usage accounting, cost estimation, and instrumentation."""

from decimal import Decimal
import json
import threading
from typing import TYPE_CHECKING, Any, Annotated, Literal, Union, cast

from pydantic import BaseModel, Field

from tabulaflow.agents.chat.input import ChatInput, describe_chat_input

if TYPE_CHECKING:
    import pydantic_ai

_instrumented = False
_instrument_lock = threading.Lock()


def instrument_agents() -> None:
    """Enable Pydantic AI instrumentation once for this process."""
    from pydantic_ai import Agent

    global _instrumented
    if _instrumented:
        return
    with _instrument_lock:
        if not _instrumented:
            Agent.instrument_all()
            _instrumented = True


class SystemMessage(BaseModel):
    """Normalized system message in a saved trajectory."""

    role: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    """Normalized user message in a saved trajectory."""

    role: Literal["user"] = "user"
    content: str


class ToolCall(BaseModel):
    """Normalized assistant tool call and its decoded arguments.

    ``arguments`` is ``None`` when the model generated invalid JSON.
    """

    tool_call_id: str
    name: str
    arguments: dict[str, Any] | None


class AssistantMessage(BaseModel):
    """Normalized assistant text, thinking, and tool calls."""

    role: Literal["assistant"] = "assistant"
    thinking: str | None = None
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ToolResponse(BaseModel):
    """Normalized tool result or automatic retry prompt."""

    role: Literal["tool"] = "tool"
    tool_call_id: str
    response: str
    is_retry_prompt: bool = False


Message = Annotated[
    Union[AssistantMessage, ToolResponse, UserMessage, SystemMessage],
    Field(discriminator="role"),
]


class Trajectory(BaseModel):
    """Serializable, provider-neutral record of one agent conversation or run."""

    id: str = "TRJY"
    messages: list[Message]

    @classmethod
    def from_pydantic_ai_messages(
        cls, messages: "list[pydantic_ai.messages.ModelMessage]", id: str = "TRJY"
    ) -> "Trajectory":
        """Normalize Pydantic AI request/response messages into a trajectory."""
        trajectory = cls(messages=[], id=id)

        for msg in reversed(messages):
            if (
                msg.kind == "request"
                and msg.instructions is not None
                and any(part.part_kind == "user-prompt" for part in msg.parts)
            ):
                trajectory.messages.append(SystemMessage(content=msg.instructions))
                break

        for msg in messages:
            if msg.kind == "request":
                for part in msg.parts:
                    if part.part_kind == "system-prompt":
                        trajectory.messages.append(SystemMessage(content=part.content))
                    elif part.part_kind == "user-prompt":
                        trajectory.messages.append(
                            UserMessage(content=describe_chat_input(cast(ChatInput, part.content)))
                        )
                    elif part.part_kind == "tool-return":
                        if not isinstance(part.content, str):
                            raise ValueError(f"Tool return is not a string: {part.content}")
                        trajectory.messages.append(ToolResponse(response=part.content, tool_call_id=part.tool_call_id))
                    elif part.part_kind == "retry-prompt":
                        trajectory.messages.append(
                            ToolResponse(
                                response=str(part.content), tool_call_id=part.tool_call_id, is_retry_prompt=True
                            )
                        )
                    else:
                        raise ValueError(f"Unknown message part type: {part.part_kind}")
            elif msg.kind == "response":
                new_msg = AssistantMessage(content="")
                for part in msg.parts:  # type: ignore
                    if part.part_kind == "text":  # type: ignore
                        new_msg.content += part.content
                    elif part.part_kind == "tool-call":  # type: ignore
                        arguments = part.args
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except json.JSONDecodeError:
                                arguments = None
                        new_msg.tool_calls.append(
                            ToolCall(tool_call_id=part.tool_call_id, name=part.tool_name, arguments=arguments)
                        )
                    elif part.part_kind == "thinking":  # type: ignore
                        if not new_msg.thinking:
                            new_msg.thinking = part.content
                        else:
                            new_msg.thinking += "\n\n" + part.content
                    else:
                        raise ValueError(f"Unknown message part type: {part.part_kind}")
                trajectory.messages.append(new_msg)
            else:
                raise ValueError(f"Unknown message type: {msg.kind}")
        return trajectory

    def to_markdown(self) -> str:
        """Render the complete trajectory as navigable Markdown."""
        lines = [f"### Trajectory `{self.id}`"]

        index_lines = ["\n**Preview:**"]
        for i, msg in enumerate(self.messages, 1):
            anchor = f"msg-{self.id}-{i}"
            if msg.role == "system":
                preview = msg.content[:50].replace("\n", " ") + ("..." if len(msg.content) > 50 else "")
                index_lines.append(f"- [{i}. System](#{anchor}): {preview}")
            elif msg.role == "user":
                preview = msg.content[:50].replace("\n", " ") + ("..." if len(msg.content) > 50 else "")
                index_lines.append(f"- [{i}. User](#{anchor}): {preview}")
            elif msg.role == "assistant":
                if msg.tool_calls:
                    tool_names = ", ".join(f"`{tc.name}`" for tc in msg.tool_calls)
                    index_lines.append(f"- [{i}. Assistant](#{anchor}): {tool_names}")
                else:
                    preview = msg.content[:50].replace("\n", " ") + ("..." if len(msg.content) > 50 else "")
                    index_lines.append(f"- [{i}. Assistant](#{anchor}): {preview}")
            elif msg.role == "tool":
                preview = msg.response[:50].replace("\n", " ") + ("..." if len(msg.response) > 50 else "")
                index_lines.append(f"- [{i}. Tool](#{anchor}): {preview}")
        lines.extend(index_lines)
        lines.append("")

        # Build message sections with anchors
        for i, msg in enumerate(self.messages, 1):
            anchor = f"msg-{self.id}-{i}"
            if msg.role == "system":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] System:**\n')
                lines.append(f"``````\n{msg.content}\n``````")
            elif msg.role == "user":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] User:**\n')
                lines.append(f"``````\n{msg.content}\n``````")
            elif msg.role == "assistant":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] Assistant:**\n')
                s = ""
                if msg.thinking:
                    s += f"<thinking>\n{msg.thinking}\n</thinking>\n"
                if msg.content:
                    try:
                        content = json.loads(msg.content)
                        content = json.dumps(content, indent=2)
                    except Exception:
                        content = msg.content
                    s += f"{content}\n"
                for tool_call in msg.tool_calls:
                    s += f'<function name="{tool_call.name}">\n'
                    if tool_call.arguments is None:
                        s += "ARGUMENTS IS NOT A VALID JSON STRING\n"
                    else:
                        for key, value in tool_call.arguments.items():
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, indent=2)
                            else:
                                value = str(value)
                            s += f'<arg name="{key}">'
                            s += f"\n{value}\n" if "\n" in value else value
                            s += "</arg>\n"
                    s += "</function>\n"
                lines.append(f"``````\n{s.strip()}\n``````")
            elif msg.role == "tool":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] Tool:**\n')
                lines.append(f"``````\n{msg.response}\n``````")
        return "\n".join(lines)


_GENAI_PRICES_PROVIDER_MAPPINGS = {
    "openai-responses": "openai",
    "google-cloud": "google",
}


def compute_api_cost(llm: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Estimate token cost, returning zero when the model has no known price."""
    from genai_prices import Usage as GenAIUsage
    from genai_prices import calc_price

    provider, model = llm.split(":", 1)
    provider = _GENAI_PRICES_PROVIDER_MAPPINGS.get(provider, provider)

    try:
        return calc_price(
            GenAIUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            model_ref=model,
            provider_id=provider,
        ).total_price
    except LookupError:
        return Decimal(0)


class Usage(BaseModel):
    """Aggregated model requests, tokens, and estimated API cost.

    Adding usage from different models sets ``llm`` to ``"MULTI"``.
    """

    llm: str | Literal["MULTI"] | None
    api_requests: int
    input_tokens: int
    output_tokens: int
    api_cost_usd: Decimal

    def __add__(self, other: "Usage") -> "Usage":
        if self.llm is None:
            llm = other.llm
        elif other.llm is None:
            llm = self.llm
        elif self.llm == other.llm:
            llm = self.llm
        else:
            llm = "MULTI"

        return Usage(
            llm=llm,
            api_requests=self.api_requests + other.api_requests,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            api_cost_usd=self.api_cost_usd + other.api_cost_usd,
        )

    @classmethod
    def create(
        cls,
        llm: str | None = None,
        api_requests: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        api_cost_usd: float | Decimal | None = None,
    ) -> "Usage":
        """Build usage, calculating cost when it is not supplied."""
        if api_cost_usd is None:
            if api_requests == 0:
                api_cost_usd = Decimal(0)
            else:
                if llm is None:
                    raise ValueError("llm is required when api_requests > 0")
                api_cost_usd = compute_api_cost(llm, input_tokens, output_tokens)

        elif isinstance(api_cost_usd, float):
            api_cost_usd = Decimal(str(api_cost_usd))
        return cls(
            api_requests=api_requests,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            api_cost_usd=api_cost_usd,
            llm=llm,
        )

    @classmethod
    def from_pydantic_ai_usage(
        cls, usage: "pydantic_ai.usage.RunUsage | pydantic_ai.usage.RequestUsage", llm: str
    ) -> "Usage":
        """Convert Pydantic AI run or request usage for one model."""
        import pydantic_ai

        if isinstance(usage, pydantic_ai.usage.RunUsage):
            return cls.create(
                llm=llm,
                api_requests=usage.requests,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
        else:
            return cls.create(
                llm=llm,
                api_requests=1,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
