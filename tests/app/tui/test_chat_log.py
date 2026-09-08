from textual.app import App, ComposeResult
from textual.widgets import Static

from tabulaflow.app.tui.widgets.chat_log import ChatLog


class _ChatLogApp(App[None]):
    def compose(self) -> ComposeResult:
        with ChatLog(id="chat-log"):
            for index in range(30):
                yield Static(f"line {index}")


async def test_chat_log_stops_following_when_user_scrolls_up() -> None:
    app = _ChatLogApp()

    async with app.run_test(size=(40, 10)) as pilot:
        chat_log = app.query_one(ChatLog)
        chat_log.scroll_end(animate=False)
        await pilot.pause()
        chat_log.scroll_page_up(animate=False)
        await pilot.pause()
        detached_y = chat_log.scroll_y

        await chat_log.mount(Static("new output"))
        chat_log.follow_new_content()
        await pilot.pause()
        await pilot.pause()

        assert not chat_log.following_tail
        assert chat_log.scroll_y == detached_y


async def test_chat_log_resumes_following_at_the_bottom() -> None:
    app = _ChatLogApp()

    async with app.run_test(size=(40, 10)) as pilot:
        chat_log = app.query_one(ChatLog)
        chat_log.scroll_end(animate=False)
        await pilot.pause()
        chat_log.scroll_page_up(animate=False)
        await pilot.pause()
        chat_log.scroll_end(animate=False)
        await pilot.pause()

        await chat_log.mount(Static("new output"))
        chat_log.follow_new_content()
        await pilot.pause()
        await pilot.pause()

        assert chat_log.following_tail
        assert chat_log.is_vertical_scroll_end
