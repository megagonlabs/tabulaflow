"""Persistent PTY-backed bash shell tool.

One long-lived ``bash --noediting -i`` runs in a pseudo-terminal: commands are
written to it and completion is read back from a PS1 sentinel, so shell state
(cwd, env, exported vars) persists across calls. This follows the OpenHands
terminal pattern, with a few deliberate differences:

**Robust input, no pacing.**  A blocking ``write_all`` on a blocking master fd,
drained by a dedicated reader thread, plus ``--noediting`` to disable readline's
line editor.  OpenHands instead paces multi-line input with a per-line sleep to
mask readline corruption and a non-blocking partial-write that silently drops
bytes; neither failure mode exists here, so large heredocs go through at full
speed.

**Forgery-proof completion.**  The PS1 sentinel carries a per-session random
nonce, so command output cannot reproduce the marker to fake a prompt or exit
code (static-marker schemes can be spoofed by a command that prints them).

**Event-driven, eviction-proof detection.**  The reader signals new output so
the poll loop wakes immediately rather than on a fixed tick (no per-command
latency floor), and the buffer is cleared before each command so "completed" is
just "a prompt is present" — no prompt-counting or output diffing.

Unlike Codex's shell, which runs each command as a fresh ``bash -lc`` with no
cross-call state, this keeps a single persistent session.
"""

import asyncio
import codecs
import json
import logging
import os
import re
import secrets
import shutil
import signal
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

# pty is POSIX-only. Guard the import so this module (and therefore the whole
# toolhub package) still loads on Windows; the tool raises a clear error at construction
# there instead of a cryptic ImportError. See ``ExecuteBashTool.__init__``.
try:
    import pty

    _POSIX = True
except ImportError:  # pragma: no cover - Windows only
    _POSIX = False

logger = logging.getLogger(__name__)

_ANSI_ESCAPE = re.compile(
    r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC: ESC ] ... terminated by BEL or ST
    r"|\x1b[\[\]][0-9;?]*[a-zA-Z]"  # CSI: ESC [ ... final letter
    r"|\x1b[()][A-Za-z0-9]"  # charset designation: ESC ( / ESC ) X
    r"|\x1b[0-9A-Za-z=><]"  # single-final escapes: ESC 7/8/c/=/> etc.
)
_MAX_OUTPUT_CHARS = 30000
_NO_CHANGE_TIMEOUT = 30
_POLL_INTERVAL = 0.5
_HISTORY_LIMIT = 10000
# Upper bound on how long a blocking write_all of the command may take. A
# normal write finishes in milliseconds; hitting this means the shell is not
# draining stdin (e.g. a foreground process ignoring input), so we reset.
_WRITE_TIMEOUT = 10.0


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
        command_filter: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize the bash tool.

        Args:
            working_dir: Initial working directory for the shell session.
            no_change_timeout: Seconds with no new output before returning.
            max_output_chars: Maximum characters in returned output.
            init_commands: Commands to run at session startup (e.g. PATH setup).
            command_filter: Optional guard function. Called with each new command
                string before execution. Return ``None`` to allow it, or a short
                reason string to block it (surfaced to the caller).
        """
        if not _POSIX:
            raise RuntimeError("ExecuteBashTool requires macOS or Linux; the shell tool is not supported on Windows.")
        self._working_dir = working_dir or os.getcwd()
        self._no_change_timeout = no_change_timeout
        self._max_output_chars = max_output_chars
        self._init_commands = init_commands or []
        self._command_filter = command_filter
        self._metrics = BashToolMetrics()

        # The completion sentinel carries a per-session random nonce so a child
        # command cannot forge a prompt by printing the marker bytes in its output
        # (the tool reads stdout in-band and otherwise cannot tell them apart).
        nonce = secrets.token_hex(16)
        self._ps1_begin = f"\n###PS1JSON_{nonce}###\n"
        self._ps1_end = f"\n###PS1END_{nonce}###"
        self._ps1_regex = re.compile(
            rf"^{re.escape(self._ps1_begin.strip())}"
            rf"((?:(?!{re.escape(self._ps1_begin.strip())}).)*?)"
            rf"{re.escape(self._ps1_end.strip())}",
            re.DOTALL | re.MULTILINE,
        )

        self._process: subprocess.Popen[bytes] | None = None
        self._pty_fd: int | None = None
        self._buf: deque[str] = deque(maxlen=_HISTORY_LIMIT + 50)
        self._buf_lock = threading.Lock()
        self._dropped_lines = 0
        self._reader_thread: threading.Thread | None = None
        # Signalled (cross-thread) by the reader whenever new output lands, so the
        # poll loop wakes immediately on output instead of sleeping a fixed tick.
        self._data_event: asyncio.Event | None = None
        # Streaming UTF-8 decoder: a multibyte char split across two PTY reads
        # must not be decoded as two invalid fragments. Recreated per session.
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._loop: asyncio.AbstractEventLoop | None = None
        # Serializes _execute: one PTY/session is single-tenant, so concurrent
        # calls would interleave bytes and steal each other's output/exit codes.
        self._lock = asyncio.Lock()
        self._initialized = False
        self._closed = False

        self._prev_status: str | None = None

    def _build_ps1(self) -> str:
        """Build a PS1 prompt that emits nonce-tagged JSON metadata each display."""
        json_str = json.dumps({"exit_code": "$?", "cwd": "$(pwd)"}, indent=2)
        return self._ps1_begin + json_str.replace('"', r"\"") + self._ps1_end + "\n"

    def _find_ps1_matches(self, text: str) -> list[re.Match[str]]:
        """Find all valid PS1 JSON metadata blocks in terminal output."""
        matches: list[re.Match[str]] = []
        for m in self._ps1_regex.finditer(text):
            try:
                json.loads(m.group(1).strip())
                matches.append(m)
            except json.JSONDecodeError:
                pass
        return matches

    # -- session lifecycle -----------------------------------------------------

    async def _initialize(self) -> None:
        """Create PTY, spawn interactive bash, configure PS1."""
        if self._initialized:
            return

        bash_path = shutil.which("bash")
        if bash_path is None:
            raise RuntimeError("Could not find bash in PATH")

        ps1 = self._build_ps1()
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        env = os.environ.copy()
        env["PS1"] = ps1
        env["PS2"] = ""
        env["TERM"] = "xterm-256color"

        master_fd, slave_fd = pty.openpty()
        try:
            # --noediting disables readline's interactive line editor. We feed
            # commands programmatically, so its history/cursor handling is unused
            # and its redisplay interleaves bytes when a large multi-line command
            # arrives faster than it can process — corrupting the input. We keep
            # interactive mode (-i) for job control and PS1 prompts.
            self._process = subprocess.Popen(
                [bash_path, "--noediting", "-i"],
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

        self._loop = asyncio.get_running_loop()
        self._data_event = asyncio.Event()
        # Keep the master fd BLOCKING and drain it on a dedicated thread. Reading
        # output concurrently with writing input is what lets a blocking write_all
        # of the command always complete: bash never stalls on a full stdout buffer,
        # so it keeps consuming stdin and the kernel input buffer keeps draining.
        self._reader_thread = threading.Thread(target=self._read_loop, args=(master_fd,), daemon=True)
        self._reader_thread.start()
        self._initialized = True

        init_cmd = f'set +H; export PROMPT_COMMAND=\'export PS1="{ps1}"\'; export PS2=""'
        self._write_pty(init_cmd.encode() + b"\n")
        await self._wait_for_prompt(timeout=5.0)
        self._clear_screen()

        # Re-apply working directory after bash init (e.g. direnv may override cwd)
        abs_wd = os.path.abspath(self._working_dir)
        self._write_pty(f"cd {abs_wd!r}\n".encode())
        await self._wait_for_prompt(timeout=5.0)
        self._clear_screen()

        for cmd in self._init_commands:
            self._write_pty(cmd.encode() + b"\n")
            await self._wait_for_prompt(timeout=10.0)
            self._clear_screen()

        # Let the reader thread drain any remaining PTY output, then clear
        await asyncio.sleep(0.1)
        with self._buf_lock:
            self._reset_buf()

    async def _ensure_session(self) -> None:
        """Restart the session if the process died."""
        if not self._initialized or self._closed or (self._process and self._process.poll() is not None):
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
                            os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
        except Exception:
            pass
        finally:
            if self._pty_fd is not None:
                # Closing the master fd makes the reader thread's blocking os.read
                # return/raise, so it can exit and be joined below.
                try:
                    os.close(self._pty_fd)
                except Exception:
                    pass
                self._pty_fd = None
            if self._reader_thread is not None:
                self._reader_thread.join(timeout=1)
                self._reader_thread = None
            self._loop = None
            self._process = None
            self._initialized = False
            self._closed = True
            self._data_event = None
            with self._buf_lock:
                self._reset_buf()
            self._prev_status = None

    # -- low-level I/O ---------------------------------------------------------

    def _write_pty(self, data: bytes) -> None:
        """Write all bytes to the PTY, blocking until the kernel accepts them.

        The master fd is blocking, so when its input buffer fills this parks
        (on a worker thread) until the reader thread drains bash's output and
        bash consumes more stdin — rather than dropping the unwritten tail, the
        failure mode of a single non-blocking ``os.write`` that ignores its
        return count.
        """
        fd = self._pty_fd
        if fd is None:
            raise RuntimeError("PTY not initialized")
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            view = view[n:]

    def _read_loop(self, fd: int) -> None:
        """Drain the PTY master on a background thread until the fd closes (EOF)."""
        while True:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            # Stateful decode: a multibyte char split across reads is held until
            # its continuation bytes arrive, instead of producing two U+FFFD.
            text = self._decoder.decode(chunk)
            with self._buf_lock:
                self._buf_append(text)
            loop, ev = self._loop, self._data_event
            if loop is not None and ev is not None:
                try:
                    loop.call_soon_threadsafe(ev.set)
                except RuntimeError:  # loop already closed during teardown
                    pass

    def _buf_append(self, text: str) -> None:
        """Append text to the buffer, keeping one line per deque entry."""
        if self._buf and not self._buf[-1].endswith("\n"):
            text = self._buf.pop() + text
        lines = text.split("\n")
        for line in lines[:-1]:
            self._append_line(line + "\n")
        if lines[-1]:
            self._append_line(lines[-1])

    def _append_line(self, item: str) -> None:
        """Append one entry, counting any maxlen-eviction so loss is reportable."""
        if len(self._buf) == self._buf.maxlen:
            self._dropped_lines += 1
        self._buf.append(item)

    def _reset_buf(self) -> None:
        """Clear the buffer and eviction counter. Caller must hold ``_buf_lock``."""
        self._buf.clear()
        self._dropped_lines = 0

    def _read_screen(self) -> str:
        """Snapshot the current buffer, stripping ANSI escapes and \\r."""
        with self._buf_lock:
            raw = "".join(self._buf)
        return _ANSI_ESCAPE.sub("", raw.replace("\r", ""))

    def _clear_screen(self) -> None:
        """Truncate the buffer to the last PS1 block."""
        with self._buf_lock:
            if not self._buf:
                return
            data = "".join(self._buf)
            begin = data.rfind(self._ps1_begin.strip())
            end = data.rfind(self._ps1_end.strip())
            self._reset_buf()
            if begin != -1 and end != -1 and end >= begin:
                self._buf.append(data[begin:])

    async def _wait_for_prompt(self, timeout: float = 5.0) -> bool:
        """Wait until the PS1 end marker appears in the buffer."""
        pat = re.compile(re.escape(self._ps1_end.strip()) + r"\s*$")
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._buf_lock:
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

    async def _send_command(self, command: str) -> str | None:
        """Write a command to the PTY on a worker thread (blocking write_all).

        The reader thread keeps draining output so the write completes even for
        large multi-line input. Returns ``None`` on success, or an ``(error: …)``
        string if the PTY is gone (e.g. EIO after the process died), after marking
        the session dead so the next call restarts it.
        """
        loop = self._loop
        assert loop is not None
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, self._send_keys, command, not self._is_special_key(command)),
                timeout=_WRITE_TIMEOUT,
            )
        except (TimeoutError, asyncio.TimeoutError):
            self._metrics.num_errors += 1
            # Closing the fd unblocks the worker thread stuck in os.write so the
            # session can be torn down without _close_internal's exit-write hanging.
            if self._pty_fd is not None:
                try:
                    os.close(self._pty_fd)
                except OSError:
                    pass
                self._pty_fd = None
            await self._close_internal()
            return "(error: timed out writing command to shell; session reset.)"
        except OSError as e:
            self._metrics.num_errors += 1
            await self._close_internal()
            return f"(error: shell session is gone: {e})"
        return None

    # -- output helpers --------------------------------------------------------

    @staticmethod
    def _is_special_key(cmd: str) -> bool:
        c = cmd.strip()
        return len(c) == 3 and c.startswith("C-")

    @staticmethod
    def _strip_command_echo(output: str, command: str) -> str:
        return output.lstrip().removeprefix(command.strip()).lstrip()

    def _truncate(self, text: str) -> str:
        if len(text) <= self._max_output_chars:
            return text
        half = self._max_output_chars // 2
        return text[:half] + f"\n\n... (output truncated: {len(text)} chars total) ...\n\n" + text[-half:]

    def _consume_output(self, body: str, command: str) -> str:
        """Strip the command echo, truncate, and clear the consumed buffer.

        Clearing here is what makes the next poll/command start from a clean
        slate: the buffer always holds only output produced since the last
        return, so completion is simply "a prompt is present" — no diffing a
        prior snapshot against a bounded buffer that may have evicted it.
        """
        out = self._truncate(self._strip_command_echo(body, command).rstrip())
        with self._buf_lock:
            dropped = self._dropped_lines
            self._reset_buf()
        if dropped:
            out = f"... ({dropped} earlier lines dropped) ...\n{out}"
        return out

    async def _wait_for_output(self, start: float, last_change: float, timeout: float | None) -> None:
        """Block until new output arrives or the next timeout check is due.

        Wakes immediately when the reader signals fresh bytes (no fixed-tick
        latency floor) but never sleeps past the active timeout boundary.
        """
        now = time.time()
        remaining = (
            (timeout - (now - start)) if timeout is not None else (self._no_change_timeout - (now - last_change))
        )
        budget = min(_POLL_INTERVAL, remaining)
        if budget <= 0:
            return
        ev = self._data_event
        if ev is None:
            await asyncio.sleep(budget)
            return
        try:
            await asyncio.wait_for(ev.wait(), budget)
        except (TimeoutError, asyncio.TimeoutError):
            pass
        ev.clear()

    # -- main execution loop ---------------------------------------------------

    async def _execute(self, command: str, is_input: bool, timeout: float | None) -> str:
        await self._ensure_session()
        command = command.strip()

        if command and not is_input and self._command_filter is not None:
            reason = self._command_filter(command)
            if reason is not None:
                self._metrics.num_errors += 1
                return f"(error: command blocked: {reason})"

        running = self._prev_status in ("no_change_timeout", "hard_timeout")

        if not running:
            if is_input:
                self._metrics.num_errors += 1
                if not command:
                    return "(error: no running command to retrieve output from.)"
                return "(error: no running command to interact with.)"
        elif not is_input and command:
            self._metrics.num_errors += 1
            return (
                "(error: previous command is still running. Use is_input=true to interact, or send C-c to interrupt.)"
            )

        # A fresh command starts from a clean buffer so that any prompt we later
        # see is unambiguously this command's. Resume polls (is_input) keep the
        # buffer, returning only output produced since the previous poll.
        if command and not is_input:
            with self._buf_lock:
                self._reset_buf()

        if command:
            error = await self._send_command(command)
            if error is not None:
                return error

        start = time.time()
        last_change = start
        last_screen = self._read_screen()

        while True:
            await self._wait_for_output(start, last_change, timeout)

            screen = self._read_screen()
            ps1s = self._find_ps1_matches(screen)

            if screen != last_screen:
                last_screen = screen
                last_change = time.time()

            # 1) Completed — our prompt reappeared (only this command's prompt
            #    can be in the freshly-cleared buffer).
            if ps1s:
                meta = _parse_ps1_metadata(ps1s[0])
                out = self._consume_output(screen[: ps1s[0].start()], command)
                self._prev_status = "completed"
                result = f"{out}\n[exit_code: {meta['exit_code']}]"
                if meta["cwd"]:
                    result += f"\n[Current working directory: {meta['cwd']}]"
                return result

            # 2) No-change timeout (skipped when per-call timeout is set,
            #    since the caller explicitly chose to wait longer)
            if timeout is None and (time.time() - last_change >= self._no_change_timeout):
                out = self._consume_output(screen, command)
                self._prev_status = "no_change_timeout"
                self._metrics.num_timeouts += 1
                return (
                    f"{out}\n\n"
                    f"[No new output for {self._no_change_timeout}s. exit_code: -1]\n"
                    "Send empty command with is_input=true to check, or C-c to interrupt."
                )

            # 3) Hard timeout (only when per-call timeout is set)
            if timeout is not None and time.time() - start >= timeout:
                out = self._consume_output(screen, command)
                self._prev_status = "hard_timeout"
                self._metrics.num_timeouts += 1
                return (
                    f"{out}\n\n"
                    f"[Command timed out after {timeout}s. exit_code: -1]\n"
                    "Send empty command with is_input=true to check, or C-c to interrupt."
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
        async with self._lock:
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
