from pathlib import Path

from pydantic_ai.messages import BinaryContent
import pytest
from textual.app import App, ComposeResult

from tabulaflow.app.tui.widgets import input as input_module
from tabulaflow.app.tui.widgets.input import HistoryInput


class _InputApp(App[None]):
    def __init__(self, history_path: Path) -> None:
        super().__init__()
        self._history_path = history_path

    def compose(self) -> ComposeResult:
        yield HistoryInput(self._history_path, id="input")


def test_build_chat_input_preserves_text_and_image_order(tmp_path: Path) -> None:
    input_bar = HistoryInput(tmp_path / "history.jsonl")
    paste_id = input_bar._register_paste("pasted\ntext")
    image = BinaryContent(b"image", media_type="image/png")
    input_bar._pending_images[3] = image

    content = input_bar.build_chat_input(f"before [Image #3] after [Pasted text #{paste_id} +2 lines]")

    assert content == ["before [Image #3]", image, " after pasted\ntext"]
    assert input_bar.build_chat_input("old [Image #2]") == "old [Image #2]"


def test_history_preserves_inactive_markers_without_reusing_ids(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    input_bar = HistoryInput(history_path)
    input_bar.record_submission("inspect [Image #7]")

    restored = HistoryInput(history_path)

    assert restored._history == ["inspect [Image #7]"]
    assert restored._image_counter == 7
    assert not restored._pending_images


async def test_active_image_markers_are_highlighted_and_deleted_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _InputApp(tmp_path / "history.jsonl")
    image = BinaryContent(b"image", media_type="image/png")
    monkeypatch.setattr(input_module, "read_clipboard_image", lambda: image)

    async with app.run_test():
        input_bar = app.query_one(HistoryInput)
        input_bar.value = "before "
        input_bar.cursor_position = len(input_bar.value)
        input_bar.action_paste()
        input_bar.insert_text_at_cursor(" after [Image #2]")
        input_bar.cursor_position = len("before [Image #1]")

        assert input_bar.highlighter is not None
        highlighted = input_bar.highlighter(input_bar.value)
        assert [(span.start, span.end) for span in highlighted.spans] == [(7, 17)]

        input_bar.cursor_position = len("before ")
        input_bar.action_cursor_right()
        assert input_bar.cursor_position == len("before [Image #1]")
        input_bar.action_cursor_left()
        assert input_bar.cursor_position == len("before ")

        input_bar.cursor_position = len("before [Image")
        assert input_bar.cursor_position == len("before [Image #1]")

        input_bar.cursor_position = len("before [Image #1]")
        input_bar.action_delete_left()

        assert input_bar.value == "before  after [Image #2]"
        assert not input_bar._pending_images
