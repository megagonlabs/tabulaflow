"""Bash tool providing a persistent shell session.

Provides a persistent bash shell session for executing commands. Environment
variables, working directory, and shell state persist across calls. Based on
the OpenHands ``execute_bash`` tool specification.
"""

import asyncio
import logging
import os
import shlex
import signal
import uuid
from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

logger = logging.getLogger(__name__)

MAX_OUTPUT_CHARS = 30000
DEFAULT_TIMEOUT = 120
INPUT_WAIT_TIMEOUT = 10


class BashToolMetrics(BaseModel):
    num_calls: int = 0
    num_input_calls: int = 0
    num_timeouts: int = 0
    num_errors: int = 0


class ExecuteBashTool:
    """Execute bash commands in a persistent shell session."""

    name: ClassVar = "execute_bash"

    def __init__(
        self,
        working_dir: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_output_chars: int = MAX_OUTPUT_CHARS,
    ) -> None:
        self._working_dir = working_dir
        self._timeout = timeout
        self._max_output_chars = max_output_chars
        self._metrics = BashToolMetrics()

        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._output_buffer: list[str] = []
        self._sentinel: str | None = None
        self._exit_code: int | None = None
        self._command_complete: asyncio.Event = asyncio.Event()
        self._command_running: bool = False
        self._session_dead: bool = False

    # -- session management ----------------------------------------------------

    async def _start_session(self) -> None:
        """Start (or restart) the persistent bash process."""
        await self.close()

        self._process = await asyncio.create_subprocess_exec(
            "bash",
            "--norc",
            "--noprofile",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self._working_dir,
            start_new_session=True,
        )
        self._session_dead = False
        self._command_running = False
        self._reader_task = asyncio.create_task(self._reader_loop())
        await self._run_init()

    async def _run_init(self) -> None:
        """Send initialization commands and wait for completion."""
        assert self._process is not None and self._process.stdin is not None
        init_sentinel = f"__BASH_INIT_{uuid.uuid4().hex[:8]}__"
        self._sentinel = init_sentinel
        self._command_complete.clear()
        self._output_buffer.clear()

        # Use a handler (not ignore) so bash survives SIGINT while children
        # get the default disposition (terminate).  trap '' would set SIG_IGN
        # which is inherited by exec'd children, making them unkillable.
        self._process.stdin.write(
            f"trap ':' INT; echo \"{init_sentinel}:0\"\n".encode()
        )
        await self._process.stdin.drain()
        try:
            await asyncio.wait_for(self._command_complete.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Bash session initialization timed out")
        self._output_buffer.clear()

    async def _ensure_session(self) -> None:
        """Ensure the bash session is alive, restarting if needed."""
        if (
            self._process is None
            or self._session_dead
            or self._process.returncode is not None
        ):
            await self._start_session()

    # -- background reader -----------------------------------------------------

    async def _reader_loop(self) -> None:
        """Background coroutine that reads stdout and detects sentinels."""
        assert self._process is not None and self._process.stdout is not None
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    self._session_dead = True
                    self._command_complete.set()
                    break
                decoded = line.decode("utf-8", errors="replace")
                if self._sentinel and self._sentinel in decoded:
                    try:
                        code_str = decoded.split(
                            f"{self._sentinel}:"
                        )[-1].strip()
                        self._exit_code = int(code_str)
                    except (ValueError, IndexError):
                        self._exit_code = -1
                    self._command_running = False
                    self._command_complete.set()
                else:
                    self._output_buffer.append(decoded)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug("Bash reader loop error: %s", e)
            self._session_dead = True
            self._command_complete.set()

    # -- helpers ---------------------------------------------------------------

    def _collect_output(self) -> str:
        """Drain the output buffer, applying truncation if needed."""
        output = "".join(self._output_buffer)
        self._output_buffer.clear()
        if len(output) > self._max_output_chars:
            half = self._max_output_chars // 2
            output = (
                output[:half]
                + f"\n\n... (output truncated: {len(output)} chars total)"
                + " ...\n\n"
                + output[-half:]
            )
        return output

    # -- command execution -----------------------------------------------------

    async def _execute_command(self, command: str) -> str:
        """Execute a new command in the persistent shell."""
        await self._ensure_session()
        assert self._process is not None and self._process.stdin is not None

        if self._command_running:
            self._metrics.num_errors += 1
            return (
                "(error: a command is still running. "
                "Use is_input=true to interact with it, "
                "or send C-c to interrupt.)"
            )

        self._output_buffer.clear()
        sentinel = f"__BASH_SENTINEL_{uuid.uuid4().hex[:16]}__"
        self._sentinel = sentinel
        self._exit_code = None
        self._command_complete.clear()
        self._command_running = True

        # Wrap in eval so the sentinel is part of the same parsed command
        # line.  This prevents stdin-reading commands (like `read`) from
        # accidentally consuming the sentinel lines from the pipe.
        wrapped = (
            f"eval {shlex.quote(command)}; "
            f"_ec=$?; echo \"{sentinel}:$_ec\"\n"
        )
        self._process.stdin.write(wrapped.encode())
        await self._process.stdin.drain()

        try:
            await asyncio.wait_for(
                self._command_complete.wait(), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            self._metrics.num_timeouts += 1
            output = self._collect_output()
            return (
                f"{output}\n\n"
                f"[Command timed out after {self._timeout}s. exit_code: -1]\n"
                f"Use is_input=true with empty command to check output, "
                f"or C-c to interrupt."
            )

        output = self._collect_output()

        if self._session_dead:
            self._metrics.num_errors += 1
            return (
                f"{output}\n"
                "[Session died unexpectedly. Will restart on next call.]"
            )

        return f"{output}[exit_code: {self._exit_code}]"

    async def _send_input(self, command: str) -> str:
        """Send input to a running process or check for more output."""
        await self._ensure_session()
        assert self._process is not None and self._process.stdin is not None

        if not self._command_running:
            self._metrics.num_errors += 1
            return (
                "(error: no command is currently running. "
                "Use is_input=false to execute a new command.)"
            )

        if command == "C-c":
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGINT)
            except (ProcessLookupError, PermissionError) as e:
                logger.debug("Failed to send SIGINT: %s", e)
        elif command == "C-z":
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTSTP)
            except (ProcessLookupError, PermissionError) as e:
                logger.debug("Failed to send SIGTSTP: %s", e)
        elif command == "C-d":
            self._process.stdin.write(b"\x04")
            await self._process.stdin.drain()
        elif command:
            self._process.stdin.write((command + "\n").encode())
            await self._process.stdin.drain()

        try:
            await asyncio.wait_for(
                self._command_complete.wait(), timeout=INPUT_WAIT_TIMEOUT
            )
        except asyncio.TimeoutError:
            pass

        output = self._collect_output()

        if self._command_complete.is_set() and not self._command_running:
            if self._session_dead:
                return (
                    f"{output}\n"
                    "[Session died. Will restart on next call.]"
                )
            return f"{output}[exit_code: {self._exit_code}]"

        return f"{output}[exit_code: -1]"

    # -- public interface (BaseTool protocol) ----------------------------------

    async def __call__(self, command: str, is_input: bool = False) -> str:
        """Execute a bash command in a persistent shell session.

        Commands run in a persistent bash process. Environment variables,
        working directory, and shell state persist between calls.

        If a previous command is still running (indicated by ``exit_code: -1``),
        set ``is_input`` to True to interact with it:

        - Send empty ``command`` to retrieve additional output.
        - Send text to write to STDIN of the running process.
        - Send ``C-c`` to interrupt (Ctrl+C), ``C-d`` for EOF, or ``C-z`` to
          suspend the running process.

        For long-running commands, run them in the background, e.g.
        ``python3 app.py > server.log 2>&1 &``.

        Args:
            command: The bash command to execute. When ``is_input`` is True,
                this is sent as input to the currently running process.
            is_input: If True, send ``command`` as input to a running process
                instead of executing it as a new command.
        """
        if is_input:
            self._metrics.num_input_calls += 1
            return await self._send_input(command)

        self._metrics.num_calls += 1
        return await self._execute_command(command)

    async def close(self) -> None:
        """Terminate the bash session and clean up resources."""
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self._process is not None and self._process.returncode is None:
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()

        self._process = None
        self._output_buffer.clear()
        self._command_running = False
        self._session_dead = False

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> BashToolMetrics:
        return self._metrics
