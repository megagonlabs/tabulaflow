"""Interactive chat session loop."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from mintq.cli.commands import handle_command, COMMAND_PREFIX
from mintq.cli.connections import ConnectionManager
from mintq.cli.display import print_banner

console = Console()


class ChatSession:
    """Holds state for a single interactive session."""

    def __init__(self, model: str, agent: str) -> None:
        self.model = model
        self.agent_name = agent
        self.connections = ConnectionManager()
        self.output_modes: set[str] = {"nl", "sql", "table"}

    @property
    def prompt_text(self) -> str:
        active = self.connections.active_alias
        if active:
            return f"mintq [{active}]> "
        return "mintq> "


async def run_chat(model: str, agent: str) -> None:
    """Main chat loop driven by prompt_toolkit."""
    session = ChatSession(model=model, agent=agent)
    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(".mintq_history"),
    )

    print_banner(console, model=model, agent=agent)

    while True:
        try:
            user_input = await prompt_session.prompt_async(session.prompt_text)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.startswith(COMMAND_PREFIX):
            should_quit = await handle_command(text, session, console)
            if should_quit:
                break
            continue

        # TODO: step 4 — send to agent, display results
        console.print("[dim italic](agent integration coming soon)[/dim italic]")
