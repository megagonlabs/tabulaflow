"""Launch the real app with conversation history primed to compact on the next turn.

    uv run scripts/app/preview_compaction.py
    uv run scripts/app/preview_compaction.py --llm-preset "Anthropic balanced"

The synthetic history carries provider usage just above the normal compaction trigger,
so the next message submitted through the standard UI exercises the production
checkpoint-and-rewrite path without sending a 240K-token fixture.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import RequestUsage
from rich.text import Text
from textual.containers import VerticalScroll

from tabulaflow.app.config import ResolvedLLMSelection, load_app_config, resolve_llm_selection
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.tui.app import _restore_terminal_modes
from tabulaflow.app.tui.widgets.chat import SystemMessage


_PRIMED_INPUT_TOKENS = 239_500


def _fixture() -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for index in range(1, 13):
        call_id = f"call-{index}"
        messages.extend(
            [
                ModelRequest(
                    parts=[
                        UserPromptPart(
                            content=(
                                f"Analyze customer cohort {index}, preserve exact identifiers, "
                                "and compare its revenue with the previous cohort."
                            )
                        )
                    ]
                ),
                ModelResponse(
                    parts=[
                        TextPart(content=f"I will query cohort {index}."),
                        ToolCallPart(
                            "run_query",
                            {"connector_alias": "sales", "query": f"SELECT * FROM cohort_{index}"},
                            call_id,
                        ),
                    ]
                ),
                ModelRequest(
                    parts=[
                        ToolReturnPart(
                            "run_query",
                            f"source_id=S{index}; cohort={index}; revenue_usd={index * 12_345}",
                            call_id,
                        )
                    ]
                ),
                ModelResponse(
                    parts=[
                        TextPart(
                            content=(
                                f"Cohort {index} has revenue ${index * 12_345:,} in source S{index}. "
                                f"The next step is to compare cohort {index + 1}."
                            )
                        )
                    ],
                    usage=(
                        RequestUsage(input_tokens=_PRIMED_INPUT_TOKENS, output_tokens=1_000)
                        if index == 12
                        else RequestUsage()
                    ),
                ),
            ]
        )
    return messages


class CompactionPreviewApp(TabulaflowApp):
    """Production TUI with a one-time synthetic conversation preload."""

    CSS_PATH = str(Path(__file__).resolve().parents[2] / "tabulaflow" / "app" / "tui" / "tui.tcss")
    _preview_loaded = False

    async def _activate_llm_option(self, selection: ResolvedLLMSelection) -> None:
        await super()._activate_llm_option(selection)
        if self._preview_loaded or self._session is None:
            return
        chat = self._session.active_chat_session
        if chat is None:
            return
        history = _fixture()
        chat._context_messages = list(history)
        chat._transcript_messages = list(history)
        self._preview_loaded = True

        chat_log = self.query_one("#chat-log", VerticalScroll)
        await chat_log.mount(
            SystemMessage(
                Text(
                    "Compaction preview ready: submit any normal message to trigger the production compaction path.",
                    style="dim",
                )
            )
        )
        chat_log.scroll_end(animate=False)


async def _run(llm_preset: str | None) -> None:
    selection = resolve_llm_selection(load_app_config(), override=llm_preset)
    if selection.preset is None:
        raise RuntimeError("Select an LLM preset in /config or pass --llm-preset")
    app = CompactionPreviewApp(
        llm_selection=selection,
        runtime_paths=RuntimePaths.create(),
        project_dir=Path.cwd(),
    )
    try:
        await app.run_async(mouse=True)
    finally:
        app._close_pane(remove_artifacts=True)
        _restore_terminal_modes()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-preset", help="Configured LLM preset label; defaults to the normal app selection")
    asyncio.run(_run(parser.parse_args().llm_preset))


if __name__ == "__main__":
    main()
