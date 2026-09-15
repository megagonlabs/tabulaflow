from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic_ai.messages import BinaryContent
import pytest
from textual.app import App, ComposeResult

from tabulaflow.app.tui.widgets import input as input_module
from tabulaflow.app.tui.widgets.input import HistoryInput
from tabulaflow.app.tui.widgets.suggestions import InputSuggester, InputSuggestion, InputSuggestionMenu


class _InputApp(App[None]):
    def __init__(self, history_path: Path) -> None:
        super().__init__()
        self._history_path = history_path

    def compose(self) -> ComposeResult:
        yield InputSuggestionMenu(id="input-suggestions")
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


def test_history_appends_without_overwriting_entries_from_another_session(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    first = HistoryInput(history_path)
    second = HistoryInput(history_path)

    first.record_submission("from first")
    second.record_submission("from second")

    assert HistoryInput(history_path)._history == ["from first", "from second"]


def test_sensitive_history_remains_available_only_in_memory(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    input_bar = HistoryInput(history_path)
    command = "/connect neo4j+s://alice:secret@example.com"

    input_bar.record_submission(command, persist=False)

    assert input_bar._history == [command]
    assert not history_path.exists()


def test_history_serializes_concurrent_appends(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    inputs = [HistoryInput(history_path) for _ in range(10)]

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(input_bar.record_submission, str(index)) for index, input_bar in enumerate(inputs)]
        for future in futures:
            future.result()

    assert set(HistoryInput(history_path)._history) == set(map(str, range(10)))


def test_history_compaction_retains_newest_complete_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr(input_module, "_MAX_HISTORY_BYTES", 300)
    input_bar = HistoryInput(history_path)

    input_bar.record_submission("a" * 100)
    input_bar.record_submission("b" * 100)
    input_bar.record_submission("newest")

    restored = HistoryInput(history_path)
    assert restored._history[-1] == "newest"
    assert history_path.stat().st_size <= 300


def test_history_persistence_failure_does_not_reject_submission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_bar = HistoryInput(tmp_path / "history.jsonl")

    def fail(_entry: str) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr(input_bar, "_append_history", fail)

    input_bar.record_submission("still accepted")

    assert input_bar._history == ["still accepted"]


async def test_input_soft_wraps_and_grows_to_five_rows(tmp_path: Path) -> None:
    app = _InputApp(tmp_path / "history.jsonl")

    async with app.run_test(size=(40, 20)) as pilot:
        input_bar = app.query_one(HistoryInput)
        input_bar.value = "x" * 100
        await pilot.pause()

        assert input_bar.soft_wrap
        assert input_bar.size.height == 3

        input_bar.value = "x" * 500
        await pilot.pause()

        assert input_bar.size.height == 5
        assert input_bar.wrapped_document.height > input_bar.size.height


async def test_slash_suggestions_can_be_navigated_and_accepted(tmp_path: Path) -> None:
    app = _InputApp(tmp_path / "history.jsonl")

    async with app.run_test() as pilot:
        input_bar = app.query_one(HistoryInput)
        menu = app.query_one(InputSuggestionMenu)
        input_bar.focus()
        await pilot.press("/")
        await pilot.pause()

        assert [item.value for item in menu.suggestions] == [
            "/help",
            "/exit",
            "/clear",
            "/config",
            "/connect",
            "/disconnect",
        ]

        await pilot.press("down", "enter")

        assert input_bar.value == "/exit"
        assert not menu.suggestions


async def test_slash_suggestion_menu_regrows_when_filter_is_deleted(tmp_path: Path) -> None:
    app = _InputApp(tmp_path / "history.jsonl")

    async with app.run_test() as pilot:
        input_bar = app.query_one(HistoryInput)
        menu = app.query_one(InputSuggestionMenu)
        input_bar.focus()
        await pilot.press(*"/connect")
        await pilot.press(*(["backspace"] * 6))
        await pilot.pause()

        assert input_bar.value == "/c"
        assert [item.value for item in menu.suggestions] == ["/clear", "/config", "/connect"]
        assert menu.size.height == 3


def test_connect_path_suggestions_include_supported_files_and_directories(tmp_path: Path) -> None:
    (tmp_path / "data.csv").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "nested").mkdir()

    suggestions = InputSuggester().get_suggestions(f"/connect {tmp_path}/")

    assert [item.label for item in suggestions] == [str(tmp_path / "data.csv"), f"{tmp_path / 'nested'}/"]


def test_suggestion_menu_scrolls_through_a_window_of_eight() -> None:
    menu = InputSuggestionMenu()
    menu.set_suggestions(tuple(InputSuggestion(str(index), str(index)) for index in range(10)))

    for _ in range(8):
        menu.move_selection(1)

    assert menu.selected == InputSuggestion("8", "8")
    assert menu.render().plain.splitlines() == [str(index) for index in range(1, 9)]

    menu.move_selection(1)
    assert menu.render().plain.splitlines() == [str(index) for index in range(2, 10)]

    menu.move_selection(1)
    assert menu.selected == InputSuggestion("0", "0")
    assert menu.render().plain.splitlines() == [str(index) for index in range(8)]


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
