import asyncio
from collections.abc import AsyncIterator

import pytest

from tabulaflow.toolhub.execute_bash import ExecuteBashTool


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


class TestLargeMultilineInput:
    async def test_large_heredoc_completes(self) -> None:
        """A heredoc far larger than the PTY kernel input buffer must not hang.

        Regression for the non-blocking partial-write byte-drop: a single
        ``os.write`` on an ``O_NONBLOCK`` master fd dropped the unwritten tail
        (including the heredoc terminator), so ``python3 -`` waited on stdin
        forever. The blocking ``write_all`` + threaded reader must push it all.
        """
        tool = ExecuteBashTool(no_change_timeout=5, max_output_chars=60000)
        try:
            body = "\n".join(f"a{i} = {i}" for i in range(400))
            cmd = f"python3 - <<'PY'\n{body}\nprint('SUM', a0 + a399)\nprint('DONE_MARKER')\nPY"
            result = await tool(cmd, timeout=30)
            assert "DONE_MARKER" in result
            assert "SUM 399" in result
            assert "[exit_code: 0]" in result
        finally:
            await tool.close()


class TestRobustness:
    async def test_output_cannot_forge_completion(self, bash: ExecuteBashTool) -> None:
        """A command printing the (un-nonced) sentinel must not forge a prompt.

        The real exit code comes from bash's nonce-tagged PS1, so the forged
        block in command output is ignored.
        """
        fake = r'printf "\n###PS1JSON###\n{\"exit_code\": \"123\", \"cwd\": \"/FAKE\"}\n###PS1END###\n"'
        result = await bash(f"( {fake}; exit 7 )")
        assert "[exit_code: 7]" in result
        assert "[exit_code: 123]" not in result
        assert "[Current working directory: /FAKE]" not in result

    async def test_multibyte_utf8_not_corrupted(self) -> None:
        """A multibyte char split across PTY read boundaries must not become U+FFFD."""
        tool = ExecuteBashTool(no_change_timeout=5, max_output_chars=500000)
        try:
            result = await tool("python3 -c \"print('€' * 100000)\"", timeout=30)
            assert "�" not in result
            assert result.count("€") >= 100000
        finally:
            await tool.close()

    async def test_multi_command_returns_all_output(self) -> None:
        """Newline-separated statements in one call must all run and all output
        captured (regression: bash prints a prompt between them and we used to
        stop at the first). Multi-line commands run as one sourced script."""
        tool = ExecuteBashTool(no_change_timeout=6, max_output_chars=50000)
        try:
            cmd = "echo FIRST_OUT\nprintf 'mid\\n'\necho SECOND_OUT\nfind . -maxdepth 1 -type d | head -3\necho THIRD_OUT"
            result = await tool(cmd, timeout=15)
            assert "FIRST_OUT" in result
            assert "SECOND_OUT" in result
            assert "THIRD_OUT" in result
            assert "[exit_code: 0]" in result
        finally:
            await tool.close()

    async def test_multi_command_state_persists(self, bash: ExecuteBashTool) -> None:
        """`cd` in a sourced multi-line command must persist to later calls."""
        await bash("cd /tmp\necho moved")
        result = await bash("pwd")
        assert "/tmp" in result

    async def test_large_command_echo_not_leaked(self) -> None:
        """A large command's source must not appear in the result.

        tty ECHO is off, so the fast-echo-overflow that dropped a chunk of the
        captured command text (garbling it and leaking it through the failed
        echo-strip) cannot happen.
        """
        tool = ExecuteBashTool(no_change_timeout=6, max_output_chars=500000)
        try:
            lines = ["python3 - <<'PY'", "rows = []"]
            for k in range(40):
                lines.append(f"rows.append({{'key_{k}': 'value {k} padding text xxxxxxxx', 'n': {k}}})")
            lines += ["print('RAN_OK', len(rows))", "PY"]
            result = await tool("\n".join(lines), timeout=30)
            assert "RAN_OK 40" in result
            assert "[exit_code: 0]" in result
            assert "rows.append" not in result  # echoed source must not leak in
        finally:
            await tool.close()

    async def test_fast_command_low_latency(self, bash: ExecuteBashTool) -> None:
        """Completion is event-driven, so a trivial command returns well under
        the old fixed 0.5s poll-interval floor."""
        import time

        await bash("echo warmup")  # pay session init once
        t0 = time.monotonic()
        result = await bash("echo quick")
        dt = time.monotonic() - t0
        assert "quick" in result
        assert "[exit_code: 0]" in result
        assert dt < 0.4

    async def test_eviction_reports_dropped_lines(self) -> None:
        """Output exceeding the line buffer reports dropped lines instead of
        silently losing the start."""
        tool = ExecuteBashTool(no_change_timeout=8, max_output_chars=200000)
        try:
            result = await tool("seq 1 20000", timeout=30)
            assert "earlier lines dropped" in result
            assert "[exit_code: 0]" in result
        finally:
            await tool.close()

    async def test_huge_output_with_trailing_completes(self) -> None:
        """Completion must be detected for output larger than the buffer even
        when a backgrounded write lands after the prompt (regression for the
        eviction-vs-initial_ps1_n miss that returned a false exit_code:-1)."""
        tool = ExecuteBashTool(no_change_timeout=6, max_output_chars=5000)
        try:
            result = await tool("seq 1 300000; { sleep 0.3; echo TRAIL; } &", timeout=20)
            assert "[exit_code: 0]" in result
        finally:
            await tool.close()

    async def test_concurrent_calls_serialized(self, bash: ExecuteBashTool) -> None:
        """Concurrent __call__s queue on the lock instead of scrambling the PTY."""
        r1, r2 = await asyncio.gather(
            bash("echo AAA; sleep 0.3; echo AAA_END"),
            bash("echo BBB; sleep 0.3; echo BBB_END"),
        )
        outs = (r1, r2)
        assert any("AAA_END" in r and "BBB" not in r for r in outs)
        assert any("BBB_END" in r and "AAA" not in r for r in outs)


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
            command_filter=lambda cmd: "no rm allowed" if cmd.strip().startswith("rm ") else None,
        )
        try:
            result = await tool("rm -rf /tmp/something")
            assert "error" in result.lower()
            assert "blocked" in result
            assert "no rm allowed" in result
            assert tool.metrics().num_errors == 1

            result = await tool("echo safe")
            assert "safe" in result
            assert "[exit_code: 0]" in result
        finally:
            await tool.close()

    async def test_filter_does_not_block_input(self) -> None:
        tool = ExecuteBashTool(command_filter=lambda cmd: "blocked", no_change_timeout=3)
        try:
            result = await tool("hello", is_input=True)
            assert "error" in result.lower()
            assert "blocked" not in result
        finally:
            await tool.close()


class TestPydanticAi:
    def test_as_pydantic_ai_tool(self) -> None:
        tool = ExecuteBashTool()
        pai_tool = tool.as_pydantic_ai_tool()
        assert pai_tool.name == "execute_bash"
