"""Shared mechanics for managed benchmark database runtimes."""

from __future__ import annotations

import asyncio
import shlex
import shutil
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from tabulaflow.research.benchmarks.installation import ProgressCallback

RuntimeAction = Callable[[str | None, list[str] | None, ProgressCallback], Awaitable[None]]
RuntimeCheck = Callable[[str | None, list[str] | None], Awaitable[bool]]
ReadinessCheck = Callable[[], Awaitable[bool]]


class BenchmarkRuntimeError(RuntimeError):
    """Raised when a managed benchmark runtime operation fails."""


@dataclass(frozen=True)
class BenchmarkRuntime:
    """Start and stop operations for a managed benchmark database runtime."""

    start_action: RuntimeAction
    stop_action: RuntimeAction
    ready_action: RuntimeCheck
    splits: tuple[str, ...] = ()
    default_split: str | None = None
    supports_database_selection: bool = False

    def resolve_split(self, split: str | None) -> str | None:
        """Validate and resolve an optional runtime split."""
        if not self.splits:
            if split is not None:
                raise BenchmarkRuntimeError("this benchmark runtime does not use splits")
            return None
        resolved = split or self.default_split
        if resolved is not None and resolved not in self.splits:
            choices = ", ".join(self.splits)
            raise BenchmarkRuntimeError(f"unsupported split {resolved!r}; available: {choices}")
        return resolved

    def _validate_database_selection(self, databases: list[str] | None) -> None:
        if databases and not self.supports_database_selection:
            raise BenchmarkRuntimeError("this benchmark does not support per-database runtime management")

    async def start(
        self,
        split: str | None,
        progress: ProgressCallback,
        databases: list[str] | None = None,
    ) -> None:
        self._validate_database_selection(databases)
        await self.start_action(self.resolve_split(split), databases, progress)

    async def stop(
        self,
        split: str | None,
        progress: ProgressCallback,
        databases: list[str] | None = None,
    ) -> None:
        self._validate_database_selection(databases)
        await self.stop_action(self.resolve_split(split), databases, progress)

    async def require_ready(
        self,
        benchmark: str,
        split: str | None,
        databases: list[str] | None = None,
    ) -> None:
        """Raise an actionable error when the requested runtime is not ready."""
        resolved = self.resolve_split(split) if self.splits else None
        if await self.ready_action(resolved, databases):
            return
        split_option = f" --split {resolved}" if resolved and resolved != self.default_split else ""
        database_options = ""
        if self.supports_database_selection and databases:
            database_options = "".join(f" --database {shlex.quote(database)}" for database in databases)
        raise BenchmarkRuntimeError(
            f"{benchmark} databases are not running. "
            f"Run: tabulaflow benchmark start {benchmark}{split_option}{database_options}"
        )


async def run_command(*command: str, cwd: Path | None = None) -> str:
    """Run a command and return stdout, raising a concise runtime error."""
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise BenchmarkRuntimeError(f"{command[0]} is not installed") from None
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        message = stderr.decode().strip() or stdout.decode().strip() or f"exit code {process.returncode}"
        raise BenchmarkRuntimeError(f"{' '.join(command)} failed: {message}")
    return stdout.decode().strip()


async def ensure_docker() -> None:
    """Verify that Docker and its daemon are available."""
    if shutil.which("docker") is None:
        raise BenchmarkRuntimeError("Docker is not installed")
    await run_command("docker", "info")


async def container_exists(name: str) -> bool:
    """Return whether a Docker container with the given name exists."""
    output = await run_command("docker", "ps", "-a", "--format", "{{.Names}}")
    return name in output.splitlines()


async def wait_until_ready(
    check: ReadinessCheck,
    description: str,
    *,
    timeout: float = 300,
    interval: float = 2,
) -> None:
    """Wait until an asynchronous readiness check succeeds."""
    deadline = time.monotonic() + timeout
    while True:
        if await check():
            return
        if time.monotonic() >= deadline:
            raise BenchmarkRuntimeError(f"timed out waiting for {description}")
        await asyncio.sleep(interval)


__all__ = [
    "BenchmarkRuntime",
    "BenchmarkRuntimeError",
    "container_exists",
    "ensure_docker",
    "run_command",
    "wait_until_ready",
]
