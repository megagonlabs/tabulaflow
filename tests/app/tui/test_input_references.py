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
    input_bar._active_images[3] = image

    content = input_bar.build_chat_input(f"before [Image #3] after [Pasted text #{paste_id} +2 lines]")

    assert content == ["before [Image #3]", image, " after pasted\ntext"]
    assert input_bar.build_chat_input("old [Image #2]") == "old [Image #2]"


def test_history_restores_text_references_but_not_image_references(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    input_bar = HistoryInput(history_path)
    paste_id = input_bar._register_paste("pasted\ntext")
    input_bar.record_submission(f"inspect [Pasted text #{paste_id} +2 lines] and [Image #7]")

    restored = HistoryInput(history_path)
    display = restored._history[0]

    assert display == "inspect [Pasted text #1 +2 lines] and [Image #7]"
    assert restored.build_chat_input(display) == "inspect pasted\ntext and [Image #7]"
    assert restored._image_counter == 7
    assert not restored._active_images

    assert restored.highlighter is not None
    highlighted = restored.highlighter(display)
    assert [(span.start, span.end) for span in highlighted.spans] == [(8, 8 + len("[Pasted text #1 +2 lines]"))]


async def test_active_references_are_highlighted_and_deleted_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _InputApp(tmp_path / "history.jsonl")
    image = BinaryContent(b"image", media_type="image/png")
    monkeypatch.setattr(input_module, "read_clipboard_image", lambda: image)

    async with app.run_test():
        input_bar = app.query_one(HistoryInput)
        input_bar._insert_paste_reference("pasted\ntext")
        paste_reference = input_bar.value
        input_bar.insert_text_at_cursor(" before ")
        input_bar.action_paste()
        image_reference = "[Image #1]"

        assert input_bar.highlighter is not None
        highlighted = input_bar.highlighter(input_bar.value)
        assert [(span.start, span.end) for span in highlighted.spans] == [
            (0, len(paste_reference)),
            (len(paste_reference) + len(" before "), len(input_bar.value)),
        ]

        input_bar.cursor_position = 0
        input_bar.action_cursor_right()
        assert input_bar.cursor_position == len(paste_reference)
        input_bar.action_cursor_left()
        assert input_bar.cursor_position == 0

        image_start = input_bar.value.index(image_reference)
        input_bar.cursor_position = image_start + len("[Image")
        assert input_bar.cursor_position == image_start + len(image_reference)

        input_bar.cursor_position = 0
        input_bar.action_delete_right()
        assert input_bar.value == f" before {image_reference}"

        input_bar.cursor_position = len(input_bar.value)
        input_bar.action_delete_left()
        assert input_bar.value == " before "
        assert not input_bar._active_images
