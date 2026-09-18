"""Preview the Hugging Face subset selector in the production chat UI.

uv run scripts/app/preview_hf_subset_selector.py
uv run scripts/app/preview_hf_subset_selector.py --fixture large
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from rich.text import Text
from textual.binding import Binding
from textual.widgets import Input

from tabulaflow.app.config import LLM_OFF, ResolvedLLMConfig
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.tui.app import _restore_terminal_modes
from tabulaflow.app.tui.widgets.chat import SystemMessage, UserMessage
from tabulaflow.app.tui.widgets.chat_log import ChatLog
from tabulaflow.app.tui.widgets.choice import InlineChoiceSelector


_GLUE_SUBSETS = (
    "ax",
    "cola",
    "mnli",
    "mnli_matched",
    "mnli_mismatched",
    "mrpc",
    "qnli",
    "qqp",
    "rte",
    "sst2",
    "stsb",
    "wnli",
)

_LANGUAGE_SUBSETS = tuple(
    f"{source}-{target}"
    for source in ("ar", "de", "en", "es", "fr", "hi", "ja", "ko", "pt", "ru", "sw", "zh")
    for target in ("ar", "de", "en", "es", "fr", "hi", "ja", "ko", "pt", "ru", "sw", "zh")
    if source != target
)


class SubsetSelectorPreviewApp(TabulaflowApp):
    """Production chat TUI with a synthetic subset-selection request."""

    CSS_PATH = str(Path(__file__).resolve().parents[2] / "tabulaflow" / "app" / "tui" / "tui.tcss")
    BINDINGS = [
        *TabulaflowApp.BINDINGS,
        Binding("ctrl+r", "show_selector", "Reopen subset selector"),
    ]

    def __init__(self, dataset_id: str, subsets: tuple[str, ...]) -> None:
        super().__init__(
            llm_config=ResolvedLLMConfig(LLM_OFF, None),
            runtime_paths=RuntimePaths.create(),
            project_dir=Path.cwd(),
        )
        self._preview_dataset_id = dataset_id
        self._preview_subsets = subsets

    def on_mount(self) -> None:
        super().on_mount()
        self.call_after_refresh(self._open_preview)

    async def _open_preview(self) -> None:
        chat_log = self.query_one(ChatLog)
        await chat_log.mount(UserMessage(f"/connect https://huggingface.co/datasets/{self._preview_dataset_id}"))
        chat_log.follow_new_content(force=True)
        await self._mount_preview_selector()

    def action_show_selector(self) -> None:
        self.run_worker(self._mount_preview_selector())

    async def _mount_preview_selector(self) -> None:
        selectors = self.query(InlineChoiceSelector)
        if selectors:
            selectors.first().focus()
            return
        self.query_one("#input-bar", Input).disabled = True
        chat_log = self.query_one(ChatLog)
        await chat_log.mount(InlineChoiceSelector("Choose subset", self._preview_subsets, confirm_label="Connect"))
        chat_log.follow_new_content(force=True)

    async def on_inline_choice_selector_selected(self, event: InlineChoiceSelector.Selected) -> None:
        await self._finish_preview(f"Selected {event.value!r}.")

    async def on_inline_choice_selector_cancelled(self, event: InlineChoiceSelector.Cancelled) -> None:
        await self._finish_preview("Connection cancelled.")

    async def _finish_preview(self, message: str) -> None:
        await self.query_one(InlineChoiceSelector).remove()
        chat_log = self.query_one(ChatLog)
        await chat_log.mount(SystemMessage(Text(f"{message} Press Ctrl+R to reopen the selector.", style="dim")))
        chat_log.follow_new_content(force=True)
        input_bar = self.query_one("#input-bar", Input)
        input_bar.disabled = False
        input_bar.focus()


async def _run(dataset_id: str, subsets: tuple[str, ...]) -> None:
    app = SubsetSelectorPreviewApp(dataset_id, subsets)
    try:
        await app.run_async(mouse=True)
    finally:
        app._close_pane(remove_artifacts=True)
        _restore_terminal_modes()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        choices=("glue", "large"),
        default="glue",
        help="Subset list to preview",
    )
    args = parser.parse_args()
    if args.fixture == "large":
        dataset_id = "Helsinki-NLP/opus-100"
        subsets = _LANGUAGE_SUBSETS
    else:
        dataset_id = "nyu-mll/glue"
        subsets = _GLUE_SUBSETS
    asyncio.run(_run(dataset_id, subsets))


if __name__ == "__main__":
    main()
