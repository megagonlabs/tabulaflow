"""Concurrent non-PTY Bash jobs for agent workflows.

Each call starts an independent ``bash -c`` process in the configured working
directory, so commands do not share cwd, environment, stdin, or output buffers.

Key properties
==============

**True concurrency.** Independent jobs run simultaneously rather than queuing
behind one shared shell session.

**Explicit job lifetime.** Commands may be killed when waiting expires,
detached on timeout, or returned immediately in the background. Each job owns a
process group so lifecycle operations include its descendants.

**Bounded observable output.** Each job continuously drains merged stdout and
stderr into a bounded head-and-tail snapshot under the scratch job directory.
Detached jobs return the log path and process-group id for later inspection.

**Predictable environment.** Jobs inherit a construction-time snapshot of the
launch environment plus explicit caller overrides. Shell state does not persist
between calls.

Interactive terminal behavior is intentionally outside this tool. Commands
that require a TTY can invoke Python's ``pty`` module or tmux explicitly.
"""

from __future__ import annotations

import asyncio
import codecs
import math
import os
from pathlib import Path
import re
import shutil
import signal
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import BaseModel, Field
from pydantic_ai import Tool

_DEFAULT_WAIT_TIMEOUT_SECONDS = 30.0
_DEFAULT_MAX_OUTPUT_CHARS = 30_000
_ACTIVE_JOB_WARNING_THRESHOLD = 8
_TERMINATION_GRACE_SECONDS = 1.0
_OUTPUT_READ_CHUNK_BYTES = 4096
_LOG_FLUSH_THRESHOLD_BYTES = 64 * 1024
_TERMINAL_ESCAPE = re.compile(
    r"\x1b(?:"
    r"\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC
    r"|\[[0-?]*[ -/]*[@-~]"  # CSI
    r"|[PX^_][^\x1b]*(?:\x1b\\)"  # DCS, SOS, PM, APC
    r"|[ -/]*[@-~]"  # two-character escape
    r")"
)
_UNSAFE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

BashMode: TypeAlias = Literal["kill_on_timeout", "detach_on_timeout", "background"]
WaitTimeout: TypeAlias = Annotated[float, Field(gt=0, allow_inf_nan=False)]


def _sanitize_terminal_text(text: str) -> str:
    """Remove terminal control sequences while preserving readable structure."""
    text = _TERMINAL_ESCAPE.sub("", text.replace("\r", "\n"))
    return _UNSAFE_CONTROL.sub("", text)


class BashToolMetrics(BaseModel):
    """Execution and lifecycle counters for the shell tool."""

    num_calls: int = 0
    num_background_calls: int = 0
    num_detached_calls: int = 0
    num_timeouts: int = 0
    num_errors: int = 0


class _BoundedText:
    """Bounded head-and-tail text accumulated from a stream."""

    def __init__(self, max_chars: int) -> None:
        self._max_chars = max_chars
        self._head_limit = (max_chars + 1) // 2
        self._tail_limit = max_chars - self._head_limit
        self._head = ""
        self._tail = ""
        self._total_chars = 0

    def append(self, text: str) -> None:
        if not text:
            return
        self._total_chars += len(text)
        head_room = self._head_limit - len(self._head)
        if head_room > 0:
            self._head += text[:head_room]
            text = text[head_room:]
        if text and self._tail_limit:
            self._tail = (self._tail + text)[-self._tail_limit :]

    def render(self) -> str:
        if self._total_chars <= self._max_chars:
            return self._head + self._tail
        return (
            self._head
            + f"\n\n... (output truncated: {self._total_chars} chars total) ...\n\n"
            + self._tail
        )

    @property
    def is_truncated(self) -> bool:
        return self._total_chars > self._max_chars


@dataclass(slots=True)
class _BashJob:
    id: str
    process: asyncio.subprocess.Process
    log_path: Path
    output: _BoundedText
    done: asyncio.Event = field(default_factory=asyncio.Event)
    termination_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    collector_task: asyncio.Task[None] | None = None
    error: str | None = None
    reported_running: bool = False

    @property
    def process_group(self) -> int:
        return self.process.pid


class ExecuteBashTool:
    """Run independent Bash jobs concurrently."""

    name: ClassVar = "execute_bash"

    def __init__(
        self,
        working_dir: str | os.PathLike[str] | None = None,
        *,
        job_dir: str | os.PathLike[str] | None = None,
        wait_timeout: float = _DEFAULT_WAIT_TIMEOUT_SECONDS,
        max_output_chars: int = _DEFAULT_MAX_OUTPUT_CHARS,
        env_overrides: Mapping[str, str] | None = None,
        command_filter: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize the Bash job runner.

        Args:
            working_dir: Directory in which every command starts.
            job_dir: Scratch directory for bounded job logs. A private temporary
                directory is created when omitted.
            wait_timeout: Default wall-clock wait budget for waiting modes.
            max_output_chars: Maximum retained command-output characters per job.
            env_overrides: Values merged over a snapshot of the launch environment.
            command_filter: Optional guard returning an error reason for blocked
                commands and ``None`` for allowed commands.
        """
        if os.name != "posix":
            raise RuntimeError("ExecuteBashTool requires a POSIX platform.")
        if not math.isfinite(wait_timeout) or wait_timeout <= 0:
            raise ValueError("wait_timeout must be a positive finite number")
        if max_output_chars < 1:
            raise ValueError("max_output_chars must be positive")

        self._working_dir = Path(working_dir or os.getcwd()).resolve()
        if not self._working_dir.is_dir():
            raise ValueError(f"working_dir is not a directory: {self._working_dir}")
        self._default_wait_timeout = float(wait_timeout)
        self._max_output_chars = max_output_chars
        self._command_filter = command_filter
        self._env = os.environ.copy()
        self._env.update(env_overrides or {})
        bash_path = shutil.which("bash", path=self._env.get("PATH"))
        if bash_path is None:
            raise RuntimeError("Could not find bash in PATH")
        self._bash_path = bash_path

        self._owns_job_dir = job_dir is None
        self._job_dir = Path(job_dir) if job_dir is not None else Path(tempfile.mkdtemp(prefix="bash-jobs-"))
        self._job_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._job_dir, 0o700)

        self._next_job_id = 1
        self._active_jobs: dict[str, _BashJob] = {}
        self._registry_lock = asyncio.Lock()
        self._metrics = BashToolMetrics()
        self._closed = False

    def _allocate_log(self) -> tuple[str, Path]:
        while True:
            job_id = f"J{self._next_job_id}"
            self._next_job_id += 1
            path = self._job_dir / f"{job_id}.log"
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                continue
            os.close(fd)
            return job_id, path

    async def _start_job(self, command: str) -> _BashJob:
        async with self._registry_lock:
            if self._closed:
                raise RuntimeError("ExecuteBashTool is closed")
            job_id, log_path = self._allocate_log()
            try:
                process = await asyncio.create_subprocess_exec(
                    self._bash_path,
                    "-c",
                    command,
                    cwd=self._working_dir,
                    env=self._env,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    start_new_session=True,
                )
            except BaseException:
                log_path.unlink(missing_ok=True)
                raise
            job = _BashJob(
                id=job_id,
                process=process,
                log_path=log_path,
                output=_BoundedText(self._max_output_chars),
            )
            self._active_jobs[job_id] = job
            job.collector_task = asyncio.create_task(self._collect_job(job))
            return job

    def _write_log(self, job: _BashJob, footer: str | None = None) -> None:
        text = _sanitize_terminal_text(job.output.render())
        if footer is not None:
            text = text.rstrip("\n") + ("\n" if text else "") + footer + "\n"
        temp_path = job.log_path.with_name(f".{job.log_path.name}.tmp")
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(text)
            os.replace(temp_path, job.log_path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

    async def _collect_job(self, job: _BashJob) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        bytes_since_flush = 0
        try:
            assert job.process.stdout is not None
            while chunk := await job.process.stdout.read(_OUTPUT_READ_CHUNK_BYTES):
                was_truncated = job.output.is_truncated
                job.output.append(decoder.decode(chunk))
                bytes_since_flush += len(chunk)
                if (
                    not job.output.is_truncated
                    or not was_truncated
                    or bytes_since_flush >= _LOG_FLUSH_THRESHOLD_BYTES
                ):
                    self._write_log(job)
                    bytes_since_flush = 0
            job.output.append(decoder.decode(b"", final=True))
            returncode = await job.process.wait()
            if returncode < 0:
                footer = f"[bash_job: {job.id}, state: killed, signal: {-returncode}]"
            else:
                footer = f"[bash_job: {job.id}, state: exited, exit_code: {returncode}]"
            self._write_log(job, footer)
        except Exception as exc:
            job.error = str(exc)
            self._metrics.num_errors += 1
            try:
                os.killpg(job.process_group, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await job.process.wait()
        finally:
            async with self._registry_lock:
                self._active_jobs.pop(job.id, None)
            job.done.set()

    async def _terminate_job(self, job: _BashJob) -> None:
        async with job.termination_lock:
            if job.done.is_set():
                return
            try:
                os.killpg(job.process_group, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(job.done.wait(), timeout=_TERMINATION_GRACE_SECONDS)
                return
            except TimeoutError:
                pass
            try:
                os.killpg(job.process_group, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(job.done.wait(), timeout=_TERMINATION_GRACE_SECONDS)
            except TimeoutError:
                pass

    async def _active_warning(self) -> str:
        async with self._registry_lock:
            ids = [job.id for job in self._active_jobs.values() if job.reported_running]
        if len(ids) <= _ACTIVE_JOB_WARNING_THRESHOLD:
            return ""
        return f"[warning: {len(ids)} detached shell jobs are currently running: {', '.join(ids)}]"

    @staticmethod
    def _join_parts(*parts: str) -> str:
        return "\n\n".join(part for part in parts if part)

    async def _format_running(self, job: _BashJob) -> str:
        job.reported_running = True
        warning = await self._active_warning()
        metadata = "\n".join(
            [
                "Command is still running.",
                f"[job_id: {job.id}]",
                f"[process_group: {job.process_group}]",
                f"[log: {job.log_path}]",
            ]
        )
        return self._join_parts(_sanitize_terminal_text(job.output.render()).rstrip(), metadata, warning)

    async def _format_completed(self, job: _BashJob) -> str:
        if job.error is not None:
            return f"(error: shell job {job.id} failed: {job.error})"
        returncode = job.process.returncode if job.process.returncode is not None else -1
        footer = f"[exit_code: {returncode}]"
        return self._join_parts(_sanitize_terminal_text(job.output.render()).rstrip(), footer)

    async def execute(
        self,
        command: str,
        mode: BashMode = "detach_on_timeout",
        wait_timeout: WaitTimeout | None = None,
    ) -> str:
        """Execute a Bash command and return agent-facing output text."""
        self._metrics.num_calls += 1
        command = command.strip()
        try:
            if not command:
                raise ValueError("command must not be empty")
            if mode not in {"kill_on_timeout", "detach_on_timeout", "background"}:
                raise ValueError(f"unsupported mode {mode!r}")
            if mode == "background" and wait_timeout is not None:
                raise ValueError("wait_timeout does not apply in background mode")
            if wait_timeout is not None and (not math.isfinite(wait_timeout) or wait_timeout <= 0):
                raise ValueError("wait_timeout must be a positive finite number")
            if self._command_filter is not None:
                reason = self._command_filter(command)
                if reason is not None:
                    raise ValueError(f"command blocked: {reason}")
            job = await self._start_job(command)
        except (ValueError, OSError, RuntimeError):
            self._metrics.num_errors += 1
            raise

        if mode == "background":
            self._metrics.num_background_calls += 1
            return await self._format_running(job)

        timeout = self._default_wait_timeout if wait_timeout is None else float(wait_timeout)
        try:
            await asyncio.wait_for(job.done.wait(), timeout=timeout)
        except asyncio.CancelledError:
            await asyncio.shield(self._terminate_job(job))
            raise
        except TimeoutError:
            self._metrics.num_timeouts += 1
            if job.done.is_set():
                return await self._format_completed(job)
            if mode == "detach_on_timeout":
                self._metrics.num_detached_calls += 1
                return await self._format_running(job)
            await self._terminate_job(job)
            body = _sanitize_terminal_text(job.output.render()).rstrip()
            timeout_text = f"Command timed out after {timeout:g}s; process group terminated.\n[exit_code: -1]"
            return self._join_parts(body, timeout_text)
        return await self._format_completed(job)

    async def __call__(
        self,
        command: str,
        mode: BashMode = "detach_on_timeout",
        wait_timeout: WaitTimeout | None = None,
    ) -> str:
        """Run a Bash command as an independent non-PTY job.

        Calls may execute concurrently. Every command starts in the configured
        project directory with a snapshot of TabulaFlow's launch environment;
        shell state such as ``cd`` and ``export`` does not persist across calls.

        Waiting commands use a wall-clock budget. ``detach_on_timeout`` preserves
        work and returns its job id, process-group id, and bounded scratch log when
        that budget expires. ``kill_on_timeout`` terminates the whole process group
        instead. ``background`` returns the same job metadata immediately and does
        not accept ``wait_timeout``. Detached jobs remain owned by this session and
        are terminated when it closes.

        Inspect a running job with ``tail <log>``. Stop it with
        ``kill -TERM -- -<process_group>``. The final line of a completed log
        records its exit status.

        Args:
            command: Bash source to execute.
            mode: Whether a waiting timeout kills or detaches the job, or whether
                to return it immediately in the background.
            wait_timeout: Wall-clock seconds to wait. Omit to use the session
                default. Not valid in ``background`` mode.
        """
        try:
            return await self.execute(command, mode, wait_timeout)
        except (ValueError, OSError, RuntimeError) as exc:
            return f"(error: {exc})"

    async def close(self) -> None:
        """Terminate all active jobs and release tool-owned resources."""
        async with self._registry_lock:
            if self._closed:
                return
            self._closed = True
            jobs = list(self._active_jobs.values())
        await asyncio.gather(*(self._terminate_job(job) for job in jobs), return_exceptions=True)
        await asyncio.gather(
            *(job.collector_task for job in jobs if job.collector_task is not None),
            return_exceptions=True,
        )
        if self._owns_job_dir:
            shutil.rmtree(self._job_dir, ignore_errors=True)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> BashToolMetrics:
        return self._metrics
