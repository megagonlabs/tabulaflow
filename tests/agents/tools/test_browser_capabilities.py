"""Browser suspension across concurrent fan-out calls."""

import asyncio
from types import SimpleNamespace

import pytest

from tabulaflow.agents.tools.browser.tool import ReleaseBrowserBeforeFanout, WebBrowserTool


@pytest.mark.parametrize("cancel", [False, True])
async def test_browser_stays_paused_until_all_fanouts_exit(cancel: bool) -> None:
    browser = WebBrowserTool()
    capability = ReleaseBrowserBeforeFanout(browser, frozenset({"fanout"}))
    ready = [asyncio.Event(), asyncio.Event()]
    release = [asyncio.Event(), asyncio.Event()]

    async def handler(index: int) -> str:
        ready[index].set()
        await release[index].wait()
        return "done"

    async with asyncio.timeout(5):
        tasks = [
            asyncio.create_task(
                capability.wrap_tool_execute(
                    None, call=None, tool_def=SimpleNamespace(name="fanout"), args=index, handler=handler
                )
            )
            for index in range(2)
        ]
        try:
            await asyncio.gather(*(event.wait() for event in ready))
            result = await browser.browser_navigate("https://example.com")
            assert isinstance(result, str) and "browser is paused" in result
            if cancel:
                tasks[0].cancel()
                with pytest.raises(asyncio.CancelledError):
                    await tasks[0]
            else:
                release[0].set()
                assert await tasks[0] == "done"
            result = await browser.browser_navigate("https://example.com")
            assert isinstance(result, str) and "browser is paused" in result
            release[1].set()
            assert await tasks[1] == "done"
            assert browser._suspend_depth == 0
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await browser.close()


async def test_other_tools_leave_browser_available() -> None:
    browser = WebBrowserTool()
    capability = ReleaseBrowserBeforeFanout(browser, frozenset({"fanout"}))

    async def handler(args: str) -> str:
        assert browser._suspend_depth == 0
        return args

    result = await capability.wrap_tool_execute(
        None, call=None, tool_def=SimpleNamespace(name="lookup"), args="found", handler=handler
    )
    assert result == "found"
