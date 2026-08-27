"""Run the Textual interface with representative result fixtures."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.containers import VerticalScroll

from preview_fixtures import mount_preview_widgets
from tabulaflow.app.config import LLM_OFF, ResolvedLLMSelection
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.tui.app import _restore_terminal_modes


class PreviewApp(TabulaflowApp):
    CSS_PATH = str(Path(__file__).resolve().parents[1] / "tabulaflow" / "app" / "tui" / "tui.tcss")

    def on_mount(self) -> None:
        super().on_mount()
        mount_preview_widgets(self, self.query_one("#chat-log", VerticalScroll))


async def run() -> None:
    app = PreviewApp(llm_selection=ResolvedLLMSelection(LLM_OFF, None))
    try:
        await app.run_async(mouse=True)
    finally:
        _restore_terminal_modes()


if __name__ == "__main__":
    asyncio.run(run())
