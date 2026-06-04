import asyncio
from collections.abc import AsyncIterator

import pytest

from tabulaflow.research.tools.execute_bash import ExecuteBashTool


@pytest.fixture
async def bash() -> AsyncIterator[ExecuteBashTool]:
    tool = ExecuteBashTool(
        no_change_timeout=3,
        max_output_chars=5000,
    )
    yield tool
    await tool.close()


class TestBasic:
    async def test_simple_echo(self, bash: ExecuteBashTool) -> None:
        result = await bash("echo hello")
        assert "hello" in result
        assert "[exit_code: 0]" in result

    async def test_exit_code_nonzero(self, bash: ExecuteBashTool) -> None:
        result = await bash("false")
        assert "[exit_code: 1]" in result

    async def test_working_directory_persists(self, bash: ExecuteBashTool) -> None:
        await bash("cd /tmp")
        result = await bash("pwd")
        assert "/tmp" in result
        assert "[exit_code: 0]" in result
        assert "[Current working directory: /tmp]" in result

    async def test_env_var_persists(self, bash: ExecuteBashTool) -> None:
        await bash("export MY_TEST_VAR=foobar123")
        result = await bash("echo $MY_TEST_VAR")
        assert "foobar123" in result

    async def test_stderr_captured(self, bash: ExecuteBashTool) -> None:
        result = await bash("echo err_msg >&2")
        assert "err_msg" in result

    async def test_multiline_output(self, bash: ExecuteBashTool) -> None:
        result = await bash("echo line1; echo line2; echo line3")
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result


class TestTimeout:
    async def test_no_change_timeout(self, bash: ExecuteBashTool) -> None:
        result = await bash("sleep 60")
        assert "exit_code: -1" in result

    async def test_no_change_timeout_disabled_with_per_call_timeout(self, bash: ExecuteBashTool) -> None:
        """When per-call timeout is set, no-change timeout is skipped."""
        result = await bash("sleep 60", timeout=5)
        assert "exit_code: -1" in result
        assert "timed out after 5" in result.lower()

    async def test_per_call_hard_timeout(self, bash: ExecuteBashTool) -> None:
        result = await bash("for i in $(seq 1 100); do echo $i; sleep 0.5; done", timeout=3)
        assert "exit_code: -1" in result
        assert "timed out after 3" in result.lower()

    async def test_interrupt_after_timeout(self, bash: ExecuteBashTool) -> None:
        await bash("sleep 60")
        result = await bash("C-c", is_input=True)
        assert "exit_code:" in result

    async def test_session_usable_after_interrupt(self, bash: ExecuteBashTool) -> None:
        await bash("sleep 60")
        await bash("C-c", is_input=True)
        await asyncio.sleep(0.5)
        result = await bash("echo recovered")
        assert "recovered" in result
        assert "[exit_code: 0]" in result


class TestInput:
    async def test_input_error_when_no_command_running(self, bash: ExecuteBashTool) -> None:
        result = await bash("hello", is_input=True)
        assert "error" in result.lower()

    async def test_send_stdin_to_running_process(self, bash: ExecuteBashTool) -> None:
        await bash("read line; echo got:$line")
        result = await bash("my_input", is_input=True)
        assert "got:my_input" in result


class TestTruncation:
    async def test_output_truncated(self, bash: ExecuteBashTool) -> None:
        bash._max_output_chars = 200
        result = await bash("seq 1 10000")
        assert "truncated" in result


class TestReset:
    async def test_reset_restores_clean_session(self, bash: ExecuteBashTool) -> None:
        await bash("export RESET_TEST_VAR=before")
        result = await bash("echo $RESET_TEST_VAR", reset=True)
        assert "before" not in result
        assert "[exit_code: 0]" in result

    async def test_reset_after_stuck_command(self, bash: ExecuteBashTool) -> None:
        await bash("sleep 60")
        result = await bash("echo fresh", reset=True)
        assert "fresh" in result
        assert "[exit_code: 0]" in result


class TestSessionRestart:
    async def test_restart_after_exit(self, bash: ExecuteBashTool) -> None:
        await bash("exit 0")
        result = await bash("echo restarted")
        assert "restarted" in result
        assert "[exit_code: 0]" in result


class TestMetrics:
    async def test_metrics_count(self, bash: ExecuteBashTool) -> None:
        await bash("echo a")
        await bash("echo b")
        m = bash.metrics()
        assert m.num_calls == 2
        assert m.num_input_calls == 0
        assert m.num_errors == 0

    async def test_metrics_input_count(self, bash: ExecuteBashTool) -> None:
        await bash("nope", is_input=True)
        m = bash.metrics()
        assert m.num_input_calls == 1
        assert m.num_errors == 1


class TestCommandFilter:
    async def test_filter_blocks_command(self) -> None:
        tool = ExecuteBashTool(
            command_filter=lambda cmd: not cmd.strip().startswith("rm "),
        )
        try:
            result = await tool("rm -rf /tmp/something")
            assert "error" in result.lower()
            assert "not allowed" in result
            assert tool.metrics().num_errors == 1

            result = await tool("echo safe")
            assert "safe" in result
            assert "[exit_code: 0]" in result
        finally:
            await tool.close()

    async def test_filter_does_not_block_input(self) -> None:
        tool = ExecuteBashTool(command_filter=lambda cmd: False, no_change_timeout=3)
        try:
            result = await tool("hello", is_input=True)
            assert "error" in result.lower()
            assert "not allowed" not in result
        finally:
            await tool.close()


class TestPydanticAi:
    def test_as_pydantic_ai_tool(self) -> None:
        tool = ExecuteBashTool()
        pai_tool = tool.as_pydantic_ai_tool()
        assert pai_tool.name == "execute_bash"
