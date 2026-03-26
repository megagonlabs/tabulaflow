"""Interactive chat session loop."""

from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from mintq.cli.agent import ChatAgent
from mintq.cli.commands import handle_command, COMMAND_PREFIX
from mintq.cli.connections import ConnectionManager
from mintq.cli.display import print_banner, render_nl, render_sql, render_table

DATA_DIR = Path.home() / ".mintq"

console = Console()


class ChatSession:
    """Holds state for a single interactive session."""

    def __init__(self, model: str, agent: str) -> None:
        self.model = model
        self.agent_name = agent
        self.connections = ConnectionManager()
        self.output_modes: set[str] = {"nl", "sql", "table"}
        self.chat_agent = ChatAgent(model=model)

    @property
    def prompt_text(self) -> str:
        active = self.connections.active_alias
        if active:
            return f"mintq [{active}]> "
        return "mintq> "


async def run_chat(model: str, agent: str) -> None:
    """Main chat loop driven by prompt_toolkit."""
    import mintq

    mintq.configure()

    session = ChatSession(model=model, agent=agent)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(str(DATA_DIR / "history")),
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

        connector = session.connections.active_connector
        if connector is None:
            console.print("[red]No database connected.[/red] Use /connect first.")
            continue

        try:
            result = await session.chat_agent.run(text, connector, console)
        except Exception as e:
            console.print(f"[red]Agent error:[/red] {e}")
            continue

        console.print()
        if "nl" in session.output_modes and result.text:
            render_nl(console, result.text)
        if "sql" in session.output_modes and result.sql:
            render_sql(console, result.sql)
        if "table" in session.output_modes and result.df is not None and not result.df.empty:
            render_table(console, result.df)
