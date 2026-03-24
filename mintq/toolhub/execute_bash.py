"""Bash tool providing a persistent PTY-based shell session.

Uses a pseudo-terminal with PS1-based command completion detection,
following the OpenHands terminal implementation pattern.
"""

import asyncio
import fcntl
import json
import logging
import os
import pty
import re
import shutil
import signal
import subprocess
import time
from collections import deque
from collections.abc import Callable
from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

logger = logging.getLogger(__name__)

# PS1 markers for completion detection
_PS1_BEGIN = "\n###PS1JSON###\n"
_PS1_END = "\n###PS1END###"
_PS1_REGEX = re.compile(
    rf"^{re.escape(_PS1_BEGIN.strip())}"
    rf"((?:(?!{re.escape(_PS1_BEGIN.strip())}).)*?)"
    rf"{re.escape(_PS1_END.strip())}",
    re.DOTALL | re.MULTILINE,
)

_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-9;?]*[a-zA-Z]|\([A-Z])")
_MAX_OUTPUT_CHARS = 30000
_NO_CHANGE_TIMEOUT = 30
_POLL_INTERVAL = 0.5
_HISTORY_LIMIT = 10000


def _build_ps1() -> str:
    """Build a PS1 prompt that emits JSON metadata on each display."""
    json_str = json.dumps({"exit_code": "$?", "cwd": "$(pwd)"}, indent=2)
    return _PS1_BEGIN + json_str.replace('"', r"\"") + _PS1_END + "\n"


def _find_ps1_matches(text: str) -> list[re.Match[str]]:
    """Find all valid PS1 JSON metadata blocks in terminal output."""
    matches: list[re.Match[str]] = []
    for m in _PS1_REGEX.finditer(text):
        try:
            json.loads(m.group(1).strip())
            matches.append(m)
        except json.JSONDecodeError:
            pass
    return matches


def _parse_ps1_metadata(match: re.Match[str]) -> dict[str, str | int]:
    """Extract exit code and cwd from a PS1 metadata match."""
    try:
        data = json.loads(match.group(1))
        return {
            "exit_code": int(data.get("exit_code", -1)),
            "cwd": data.get("cwd", ""),
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return {"exit_code": -1, "cwd": ""}


class BashToolMetrics(BaseModel):
    num_calls: int = 0
    num_input_calls: int = 0
    num_timeouts: int = 0
    num_errors: int = 0


class ExecuteBashTool:
    """Execute bash commands in a persistent PTY-based shell session."""

    name: ClassVar = "execute_bash"

    def __init__(
        self,
        working_dir: str | None = None,
        no_change_timeout: int = _NO_CHANGE_TIMEOUT,
        max_output_chars: int = _MAX_OUTPUT_CHARS,
        init_commands: list[str] | None = None,
        command_filter: Callable[[str], bool] | None = None,
    ) -> None:
        """Initialize the bash tool.

        Args:
            working_dir: Initial working directory for the shell session.
            no_change_timeout: Seconds with no new output before returning.
            max_output_chars: Maximum characters in returned output.
            init_commands: Commands to run at session startup (e.g. PATH setup).
            command_filter: Optional guard function. Called with each new
                command string before execution. Return ``True`` to allow,
                ``False`` to block the command.
        """
        self._working_dir = working_dir or os.getcwd()
        self._no_change_timeout = no_change_timeout
        self._max_output_chars = max_output_chars
        self._init_commands = init_commands or []
        self._command_filter = command_filter
        self._metrics = BashToolMetrics()

        self._process: subprocess.Popen | None = None
        self._pty_fd: int | None = None
        self._buf: deque[str] = deque(maxlen=_HISTORY_LIMIT + 50)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._initialized = False
        self._closed = False

        self._prev_status: str | None = None
        self._prev_output: str = ""

    # -- session lifecycle -----------------------------------------------------

    async def _initialize(self) -> None:
        """Create PTY, spawn interactive bash, configure PS1."""
        if self._initialized:
            return

        bash_path = shutil.which("bash")
        if bash_path is None:
            raise RuntimeError("Could not find bash in PATH")

        ps1 = _build_ps1()
        env = os.environ.copy()
        env["PS1"] = ps1
        env["PS2"] = ""
        env["TERM"] = "xterm-256color"

        master_fd, slave_fd = pty.openpty()
        try:
            self._process = subprocess.Popen(
                [bash_path, "-i"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=self._working_dir,
                env=env,
                text=False,
                bufsize=0,
                preexec_fn=os.setsid,
                close_fds=True,
            )
        finally:
            os.close(slave_fd)

        self._pty_fd = master_fd
        self._closed = False
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        self._loop = asyncio.get_running_loop()
        self._loop.add_reader(master_fd, self._on_data)
        self._initialized = True

        init_cmd = (
            f'set +H; export PROMPT_COMMAND=\'export PS1="{ps1}"\'; export PS2=""'
        )
        self._write_pty(init_cmd.encode() + b"\n")
        await self._wait_for_prompt(timeout=5.0)
        self._clear_screen()

        # Re-apply working directory after bash init (e.g. direnv may override cwd)
        abs_wd = os.path.abspath(self._working_dir)
        self._write_pty(f'cd {abs_wd!r}\n'.encode())
        await self._wait_for_prompt(timeout=5.0)
        self._clear_screen()

        for cmd in self._init_commands:
            self._write_pty(cmd.encode() + b"\n")
            await self._wait_for_prompt(timeout=10.0)
            self._clear_screen()

        self._buf.clear()

    async def _ensure_session(self) -> None:
        """Restart the session if the process died."""
        if (
            not self._initialized
            or self._closed
            or (self._process and self._process.poll() is not None)
        ):
            await self._close_internal()
            await self._initialize()

    async def _close_internal(self) -> None:
        """Tear down PTY, process, and event loop reader."""
        if self._closed and not self._initialized:
            return
        try:
            if self._process:
                try:
                    self._write_pty(b"exit\n")
                except Exception:
                    pass
                deadline = time.time() + 2
                while self._process.poll() is None and time.time() < deadline:
                    await asyncio.sleep(0.1)
                if self._process.poll() is None:
                    try:
                        os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                    except (ProcessLookupError, PermissionError):
                        pass
                    deadline = time.time() + 1
                    while self._process.poll() is None and time.time() < deadline:
                        await asyncio.sleep(0.1)
                    if self._process.poll() is None:
                        try:
                            os.killpg(
                                os.getpgid(self._process.pid), signal.SIGKILL
                            )
                        except (ProcessLookupError, PermissionError):
                            pass
        except Exception:
            pass
        finally:
            if self._pty_fd is not None:
                if self._loop is not None:
                    try:
                        self._loop.remove_reader(self._pty_fd)
                    except Exception:
                        pass
                try:
                    os.close(self._pty_fd)
                except Exception:
                    pass
                self._pty_fd = None
            self._loop = None
            self._process = None
            self._initialized = False
            self._closed = True
            self._buf.clear()
            self._prev_status = None
            self._prev_output = ""

    # -- low-level I/O ---------------------------------------------------------

    def _write_pty(self, data: bytes) -> None:
        if self._pty_fd is None:
            raise RuntimeError("PTY not initialized")
        os.write(self._pty_fd, data)

    def _on_data(self) -> None:
        """Event loop callback: read available PTY output into the buffer."""
        fd = self._pty_fd
        if fd is None:
            return
        try:
            while True:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                self._buf_append(text)
        except BlockingIOError:
            pass
        except OSError:
            pass

    def _buf_append(self, text: str) -> None:
        """Append text to the buffer, keeping one line per deque entry."""
        if self._buf and not self._buf[-1].endswith("\n"):
            text = self._buf.pop() + text
        lines = text.split("\n")
        for line in lines[:-1]:
            self._buf.append(line + "\n")
        if lines[-1]:
            self._buf.append(lines[-1])

    def _read_screen(self) -> str:
        """Snapshot the current buffer, stripping ANSI escapes and \\r."""
        raw = "".join(self._buf).replace("\r", "")
        return _ANSI_ESCAPE.sub("", raw)

    def _clear_screen(self) -> None:
        """Truncate the buffer to the last PS1 block."""
        if not self._buf:
            return
        data = "".join(self._buf)
        begin = data.rfind(_PS1_BEGIN.strip())
        end = data.rfind(_PS1_END.strip())
        if begin != -1 and end != -1 and end >= begin:
            self._buf.clear()
            self._buf.append(data[begin:])
        else:
            self._buf.clear()

    async def _wait_for_prompt(self, timeout: float = 5.0) -> bool:
        """Wait until the PS1 end marker appears in the buffer."""
        pat = re.compile(re.escape(_PS1_END.strip()) + r"\s*$")
        deadline = time.time() + timeout
        while time.time() < deadline:
            tail = "".join(self._buf)[-4096:]
            if pat.search(tail):
                return True
            await asyncio.sleep(0.05)
        return False

    def _send_keys(self, text: str, enter: bool = True) -> None:
        """Send keystrokes to the PTY, with Ctrl-sequence support."""
        upper = text.upper().strip()
        if upper.startswith("C-") and len(upper) == 3:
            key = upper[-1]
            if "A" <= key <= "Z":
                self._write_pty(bytes([ord(key) & 0x1F]))
                return
        payload = text.encode("utf-8", "ignore")
        if enter:
            payload += b"\n"
        self._write_pty(payload)

    # -- output helpers --------------------------------------------------------

    @staticmethod
    def _is_special_key(cmd: str) -> bool:
        c = cmd.strip()
        return len(c) == 3 and c.startswith("C-")

    @staticmethod
    def _extract_between_ps1s(
        content: str,
        matches: list[re.Match[str]],
        before_first: bool = False,
    ) -> str:
        """Return the text between PS1 blocks."""
        if not matches:
            return content
        if len(matches) == 1:
            if before_first:
                return content[: matches[0].start()]
            return content[matches[0].end() + 1 :]
        parts: list[str] = []
        for i in range(len(matches) - 1):
            parts.append(content[matches[i].end() + 1 : matches[i + 1].start()])
        return "".join(parts)

    @staticmethod
    def _strip_command_echo(output: str, command: str) -> str:
        return output.lstrip().removeprefix(command.strip()).lstrip()

    def _truncate(self, text: str) -> str:
        if len(text) <= self._max_output_chars:
            return text
        half = self._max_output_chars // 2
        return (
            text[:half]
            + f"\n\n... (output truncated: {len(text)} chars total) ...\n\n"
            + text[-half:]
        )

    def _get_output(self, command: str, raw: str) -> str:
        """Diff against prev_output, strip command echo, rstrip."""
        if self._prev_output:
            output = raw.removeprefix(self._prev_output)
        else:
            output = raw
        self._prev_output = raw
        return self._strip_command_echo(output, command).rstrip()

    # -- main execution loop ---------------------------------------------------

    async def _execute(
        self, command: str, is_input: bool, timeout: float | None
    ) -> str:
        await self._ensure_session()
        command = command.strip()

        if command and not is_input and self._command_filter is not None:
            if not self._command_filter(command):
                self._metrics.num_errors += 1
                return "(error: command is not allowed.)"

        running = self._prev_status in ("no_change_timeout", "hard_timeout")

        if not running:
            if not command and is_input:
                self._metrics.num_errors += 1
                return "(error: no running command to retrieve output from.)"
            if is_input:
                self._metrics.num_errors += 1
                return "(error: no running command to interact with.)"

        initial = self._read_screen()
        initial_ps1_n = len(_find_ps1_matches(initial))

        if (
            running
            and not initial.rstrip().endswith(_PS1_END.strip())
            and not is_input
            and command
        ):
            self._metrics.num_errors += 1
            return (
                "(error: previous command is still running. "
                "Use is_input=true to interact, or send C-c to interrupt.)"
            )

        if command:
            self._send_keys(command, enter=not self._is_special_key(command))

        start = time.time()
        last_change = start
        last_screen = initial

        while True:
            await asyncio.sleep(_POLL_INTERVAL)

            screen = self._read_screen()
            ps1s = _find_ps1_matches(screen)
            ps1_n = len(ps1s)

            if screen != last_screen:
                last_screen = screen
                last_change = time.time()

            # 1) Completed — new PS1 appeared
            if (
                ps1_n > initial_ps1_n
                or screen.rstrip().endswith(_PS1_END.strip())
            ) and ps1s:
                meta = _parse_ps1_metadata(ps1s[-1])
                before_first = ps1_n == 1
                raw = self._extract_between_ps1s(
                    screen, ps1s, before_first=before_first
                )
                out = self._truncate(self._get_output(command, raw))

                self._prev_status = "completed"
                self._prev_output = ""
                self._clear_screen()
                result = f"{out}\n[exit_code: {meta['exit_code']}]"
                if meta["cwd"]:
                    result += f"\n[Current working directory: {meta['cwd']}]"
                return result

            # 2) No-change timeout (skipped when per-call timeout is set,
            #    since the caller explicitly chose to wait longer)
            if timeout is None and (
                time.time() - last_change >= self._no_change_timeout
            ):
                raw = self._extract_between_ps1s(screen, ps1s)
                out = self._truncate(self._get_output(command, raw))

                self._prev_status = "no_change_timeout"
                self._metrics.num_timeouts += 1
                return (
                    f"{out}\n\n"
                    f"[No new output for {self._no_change_timeout}s. "
                    f"exit_code: -1]\n"
                    "Send empty command with is_input=true to check, "
                    "or C-c to interrupt."
                )

            # 3) Hard timeout (only when per-call timeout is set)
            if timeout is not None and time.time() - start >= timeout:
                raw = self._extract_between_ps1s(screen, ps1s)
                out = self._truncate(self._get_output(command, raw))

                self._prev_status = "hard_timeout"
                self._metrics.num_timeouts += 1
                return (
                    f"{out}\n\n"
                    f"[Command timed out after {timeout}s. "
                    f"exit_code: -1]\n"
                    "Send empty command with is_input=true to check, "
                    "or C-c to interrupt."
                )

    # -- BaseTool protocol -----------------------------------------------------

    async def __call__(
        self,
        command: str,
        is_input: bool = False,
        timeout: float | None = None,
        reset: bool = False,
    ) -> str:
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
            timeout: Optional hard timeout in seconds. When set, the
                no-change timeout is disabled and the command is allowed to
                run until this wall-clock limit is reached.
            reset: If True, reset the shell session before executing the
                command. Use when the session is in an unrecoverable state.
        """
        if reset:
            await self._close_internal()
        if is_input:
            self._metrics.num_input_calls += 1
        else:
            self._metrics.num_calls += 1
        return await self._execute(command, is_input, timeout)

    async def close(self) -> None:
        """Terminate the bash session and clean up resources."""
        await self._close_internal()

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> BashToolMetrics:
        return self._metrics
