import asyncio

import pytest

from mintq.toolhub.bash import ExecuteBashTool


@pytest.fixture
async def bash():
    tool = ExecuteBashTool(timeout=10, max_output_chars=5000)
    yield tool
    await tool.close()


class TestBashToolBasic:
    async def test_simple_echo(self, bash: ExecuteBashTool):
        result = await bash("echo hello")
        assert "hello" in result
        assert "[exit_code: 0]" in result

    async def test_exit_code_nonzero(self, bash: ExecuteBashTool):
        result = await bash("false")
        assert "[exit_code: 1]" in result

    async def test_working_directory_persists(self, bash: ExecuteBashTool):
        await bash("cd /tmp")
        result = await bash("pwd")
        assert "/tmp" in result
        assert "[exit_code: 0]" in result

    async def test_env_var_persists(self, bash: ExecuteBashTool):
        await bash("export MY_TEST_VAR=foobar123")
        result = await bash("echo $MY_TEST_VAR")
        assert "foobar123" in result

    async def test_stderr_captured(self, bash: ExecuteBashTool):
        result = await bash("echo err_msg >&2")
        assert "err_msg" in result

    async def test_multiline_output(self, bash: ExecuteBashTool):
        result = await bash("echo line1; echo line2; echo line3")
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result


class TestBashToolTimeout:
    async def test_timeout_returns_minus_one(self, bash: ExecuteBashTool):
        bash._timeout = 2
        result = await bash("sleep 30")
        assert "exit_code: -1" in result
        assert "timed out" in result.lower()

    async def test_interrupt_after_timeout(self, bash: ExecuteBashTool):
        bash._timeout = 2
        await bash("sleep 30")
        result = await bash("C-c", is_input=True)
        # After C-c, exit_code should be non-negative (SIGINT = 130)
        assert "exit_code:" in result

    async def test_session_usable_after_interrupt(self, bash: ExecuteBashTool):
        bash._timeout = 2
        await bash("sleep 30")
        await bash("C-c", is_input=True)
        # Allow sentinel to be processed
        await asyncio.sleep(0.5)
        result = await bash("echo recovered")
        assert "recovered" in result
        assert "[exit_code: 0]" in result


class TestBashToolInput:
    async def test_input_error_when_no_command_running(self, bash: ExecuteBashTool):
        result = await bash("hello", is_input=True)
        assert "error" in result.lower()

    async def test_send_stdin_to_running_process(self, bash: ExecuteBashTool):
        bash._timeout = 2
        await bash("read line; echo got:$line")
        result = await bash("my_input", is_input=True)
        assert "got:my_input" in result


class TestBashToolTruncation:
    async def test_output_truncated(self, bash: ExecuteBashTool):
        bash._max_output_chars = 200
        result = await bash("seq 1 10000")
        assert "truncated" in result


class TestBashToolSessionRestart:
    async def test_restart_after_exit(self, bash: ExecuteBashTool):
        await bash("exit 0")
        result = await bash("echo restarted")
        assert "restarted" in result
        assert "[exit_code: 0]" in result


class TestBashToolMetrics:
    async def test_metrics_count(self, bash: ExecuteBashTool):
        await bash("echo a")
        await bash("echo b")
        m = bash.metrics()
        assert m.num_calls == 2
        assert m.num_input_calls == 0
        assert m.num_errors == 0

    async def test_metrics_input_count(self, bash: ExecuteBashTool):
        await bash("nope", is_input=True)
        m = bash.metrics()
        assert m.num_input_calls == 1
        assert m.num_errors == 1


class TestBashToolPydanticAi:
    def test_as_pydantic_ai_tool(self):
        tool = ExecuteBashTool()
        pai_tool = tool.as_pydantic_ai_tool()
        assert pai_tool.name == "execute_bash"
