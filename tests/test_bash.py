import asyncio
import os
from pathlib import Path
import re
import stat
import time
from collections.abc import AsyncIterator

import pytest

from tabulaflow.agents.tools.shell.tool import ExecuteBashTool


@pytest.fixture
async def bash(tmp_path: Path) -> AsyncIterator[ExecuteBashTool]:
    tool = ExecuteBashTool(
        working_dir=tmp_path,
        job_dir=tmp_path / "jobs",
        wait_timeout=1,
        max_output_chars=5000,
        env_overrides={"SHELL_TEST_VALUE": "configured"},
    )
    yield tool
    await tool.close()


def _metadata(result: str, name: str) -> str:
    match = re.search(rf"^\[{re.escape(name)}: (.+)]$", result, re.MULTILINE)
    assert match is not None, result
    return match.group(1)


async def _wait_for_footer(log_path: Path, timeout: float = 3) -> str:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        text = log_path.read_text() if log_path.exists() else ""
        if "[bash_job:" in text:
            return text
        await asyncio.sleep(0.02)
    raise AssertionError(f"job did not finish; log={log_path.read_text()!r}")


class TestExecution:
    async def test_simple_command(self, bash: ExecuteBashTool) -> None:
        result = await bash("echo hello")
        assert "hello" in result
        assert "[exit_code: 0]" in result

    async def test_nonzero_exit_and_stderr(self, bash: ExecuteBashTool) -> None:
        result = await bash("echo failed >&2; exit 7")
        assert "failed" in result
        assert "[exit_code: 7]" in result

    async def test_multiline_command(self, bash: ExecuteBashTool) -> None:
        result = await bash("first=hello\necho \"$first world\"")
        assert "hello world" in result
        assert "[exit_code: 0]" in result

    async def test_shell_state_does_not_persist(self, bash: ExecuteBashTool, tmp_path: Path) -> None:
        await bash("cd /tmp; export TRANSIENT_VALUE=present")
        result = await bash('printf "%s|%s" "$PWD" "${TRANSIENT_VALUE-unset}"')
        assert f"{tmp_path}|unset" in result

    async def test_environment_override_is_available(self, bash: ExecuteBashTool) -> None:
        result = await bash('printf "%s" "$SHELL_TEST_VALUE"')
        assert "configured" in result

    async def test_commands_run_concurrently(self, bash: ExecuteBashTool) -> None:
        started = time.monotonic()
        first, second = await asyncio.gather(
            bash("sleep 0.4; echo first"),
            bash("sleep 0.4; echo second"),
        )
        elapsed = time.monotonic() - started
        assert elapsed < 0.7
        assert "first" in first and "second" not in first
        assert "second" in second and "first" not in second

    async def test_large_multiline_input_needs_no_staging(self, bash: ExecuteBashTool) -> None:
        body = "\n".join(f"a{i} = {i}" for i in range(400))
        command = f"python3 - <<'PY'\n{body}\nprint(a0 + a399)\nPY"
        result = await bash(command, wait_timeout=5)
        assert "399" in result
        assert "[exit_code: 0]" in result


class TestJobModes:
    async def test_background_returns_immediately_and_records_completion(self, bash: ExecuteBashTool) -> None:
        started = time.monotonic()
        result = await bash("sleep 0.3; echo finished", mode="background")
        assert time.monotonic() - started < 0.2
        assert _metadata(result, "job_id") == "J1"
        log_path = Path(_metadata(result, "log"))
        text = await _wait_for_footer(log_path)
        assert "finished" in text
        assert "state: exited, exit_code: 0" in text

    async def test_default_mode_detaches_on_timeout(self, bash: ExecuteBashTool) -> None:
        result = await bash("sleep 0.3; echo preserved", wait_timeout=0.05)
        assert "Command is still running." in result
        assert bash.metrics().num_detached_calls == 1
        text = await _wait_for_footer(Path(_metadata(result, "log")))
        assert "preserved" in text

    async def test_kill_on_timeout_terminates_process_group(self, bash: ExecuteBashTool) -> None:
        result = await bash("sleep 60", mode="kill_on_timeout", wait_timeout=0.05)
        assert "process group terminated" in result
        assert "[exit_code: -1]" in result
        text = await _wait_for_footer(bash._job_dir / "J1.log")
        assert "state: killed" in text

    async def test_agent_can_stop_background_process_group(self, bash: ExecuteBashTool) -> None:
        running = await bash("sleep 60", mode="background")
        process_group = _metadata(running, "process_group")
        stop = await bash(f"kill -TERM -- -{process_group}", mode="kill_on_timeout")
        assert "[exit_code: 0]" in stop
        text = await _wait_for_footer(Path(_metadata(running, "log")))
        assert "state: killed" in text

    async def test_background_rejects_wait_timeout(self, bash: ExecuteBashTool) -> None:
        result = await bash("echo no", mode="background", wait_timeout=1)
        assert result == "(error: wait_timeout does not apply in background mode)"

    async def test_cancellation_kills_unreported_job(self, bash: ExecuteBashTool) -> None:
        task = asyncio.create_task(bash("sleep 60", wait_timeout=10))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        text = await _wait_for_footer(bash._job_dir / "J1.log")
        assert "state: killed" in text


class TestLogs:
    async def test_log_names_are_sequential_and_private(self, bash: ExecuteBashTool) -> None:
        first, second = await asyncio.gather(
            bash("sleep 0.2", mode="background"),
            bash("sleep 0.2", mode="background"),
        )
        assert {_metadata(first, "job_id"), _metadata(second, "job_id")} == {"J1", "J2"}
        for result in (first, second):
            path = Path(_metadata(result, "log"))
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(bash._job_dir.stat().st_mode) == 0o700

    async def test_output_and_log_are_bounded_head_and_tail(self, tmp_path: Path) -> None:
        tool = ExecuteBashTool(working_dir=tmp_path, job_dir=tmp_path / "jobs", max_output_chars=200)
        try:
            result = await tool("seq 1 1000")
            assert "output truncated" in result
            assert "1\n" in result
            assert "1000" in result
            log = (tmp_path / "jobs" / "J1.log").read_text()
            assert "output truncated" in log
            assert "[bash_job: J1, state: exited, exit_code: 0]" in log
            assert len(log) < 400
        finally:
            await tool.close()

    async def test_running_log_flushes_small_updates(self, bash: ExecuteBashTool) -> None:
        result = await bash("echo first; sleep 0.05; echo second; sleep 1", mode="background")
        log_path = Path(_metadata(result, "log"))
        await asyncio.sleep(0.25)
        text = log_path.read_text()
        assert "first" in text and "second" in text
        assert "[bash_job:" not in text

    async def test_utf8_split_across_reads_is_not_corrupted(self, tmp_path: Path) -> None:
        tool = ExecuteBashTool(working_dir=tmp_path, job_dir=tmp_path / "jobs", max_output_chars=500_000)
        try:
            result = await tool("python3 -c \"print('€' * 100000)\"", wait_timeout=5)
            assert "�" not in result
            assert result.count("€") == 100000
        finally:
            await tool.close()


class TestLifecycle:
    async def test_close_kills_background_jobs_and_writes_footer(self, tmp_path: Path) -> None:
        tool = ExecuteBashTool(working_dir=tmp_path, job_dir=tmp_path / "jobs")
        result = await tool("sleep 60", mode="background")
        group = int(_metadata(result, "process_group"))
        log_path = Path(_metadata(result, "log"))
        await tool.close()
        text = log_path.read_text()
        assert "state: killed" in text
        with pytest.raises(ProcessLookupError):
            os.killpg(group, 0)

    async def test_many_active_jobs_return_warning(self, tmp_path: Path) -> None:
        tool = ExecuteBashTool(working_dir=tmp_path, job_dir=tmp_path / "jobs")
        try:
            results = [await tool("sleep 60", mode="background") for _ in range(9)]
            assert "warning: 9 shell jobs" in results[-1]
            assert "J1" in results[-1] and "J9" in results[-1]
        finally:
            await tool.close()


class TestValidationAndMetrics:
    async def test_execute_raises_and_call_returns_model_error(self, bash: ExecuteBashTool) -> None:
        with pytest.raises(ValueError, match="command must not be empty"):
            await bash.execute("")
        assert await bash("") == "(error: command must not be empty)"

    async def test_command_filter_blocks_before_job_creation(self, tmp_path: Path) -> None:
        tool = ExecuteBashTool(
            working_dir=tmp_path,
            job_dir=tmp_path / "jobs",
            command_filter=lambda command: "blocked" if command == "unsafe" else None,
        )
        try:
            assert await tool("unsafe") == "(error: command blocked: blocked)"
            assert not list((tmp_path / "jobs").glob("*.log"))
        finally:
            await tool.close()

    async def test_metrics(self, bash: ExecuteBashTool) -> None:
        await bash("true")
        await bash("sleep 0.2", wait_timeout=0.01)
        await bash("sleep 0.2", mode="background")
        await bash("", mode="kill_on_timeout")
        metrics = bash.metrics()
        assert metrics.num_calls == 4
        assert metrics.num_detached_calls == 1
        assert metrics.num_background_calls == 1
        assert metrics.num_timeouts == 1
        assert metrics.num_errors == 1

    def test_pydantic_ai_tool(self, tmp_path: Path) -> None:
        tool = ExecuteBashTool(working_dir=tmp_path, job_dir=tmp_path / "jobs")
        assert tool.as_pydantic_ai_tool().name == "execute_bash"
